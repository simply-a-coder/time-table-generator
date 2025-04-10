from flask import render_template, request, redirect, url_for, flash, jsonify, Response, send_from_directory
from app import app, db
from app.models.models import Course, Instructor, Classroom, TimeSlot, Student
from app.controllers.scheduler import TimetableScheduler
import networkx as nx
import os
from io import BytesIO, StringIO
import base64
import csv
import pandas as pd
from werkzeug.utils import secure_filename
import datetime

# Set the matplotlib backend to 'Agg' to avoid tkinter issues
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

@app.context_processor
def inject_current_year():
    """Add current_year to all template contexts"""
    return {'current_year': datetime.datetime.now().year}

@app.context_processor
def inject_courses_for_upload():
    """Add courses to all template contexts for the PDF upload form"""
    try:
        courses = Course.query.all()
        instructors = Instructor.query.all()
        classrooms = Classroom.query.all()
        timeslots = TimeSlot.query.all()
        return {
            'courses_for_upload': courses,
            'instructors_for_upload': instructors,
            'classrooms_for_upload': classrooms,
            'timeslots_for_upload': timeslots
        }
    except:
        return {
            'courses_for_upload': [],
            'instructors_for_upload': [],
            'classrooms_for_upload': [],
            'timeslots_for_upload': []
        }

@app.route('/')
def index():
    """Home page route with dashboard statistics"""
    # Gather statistics for the dashboard
    stats = {
        'courses': Course.query.count(),
        'instructors': Instructor.query.count(),
        'students': Student.query.count(),
        'classrooms': Classroom.query.count(),
        'scheduled_courses': Course.query.filter(Course.time_slot_id.isnot(None)).count()
    }
    
    # Get the latest courses (for illustration - in a real app, you'd track actual activities)
    recent_courses = Course.query.order_by(Course.id.desc()).limit(3).all()
    
    # Sample recent activities - in a real app, you'd store these in a database
    activities = [
        {
            'icon': 'fas fa-calendar-check',
            'description': 'Timetable generated successfully',
            'time': 'Just now',
            'user': 'System'
        }
    ]
    
    # Add recent course additions to activities
    for course in recent_courses:
        activities.append({
            'icon': 'fas fa-book',
            'description': f'Added new course: {course.code}',
            'time': '2 hours ago',  # In a real app, this would be the actual time
            'user': 'Admin'
        })
    
    return render_template('index.html', stats=stats, activities=activities)

@app.route('/courses')
def courses():
    """List all courses"""
    courses = Course.query.all()
    return render_template('courses.html', courses=courses)

@app.route('/courses/add', methods=['GET', 'POST'])
def add_course():
    """Add a new course"""
    if request.method == 'POST':
        code = request.form['code']
        name = request.form['name']
        instructor_id = request.form.get('instructor_id')
        
        course = Course(code=code, name=name, instructor_id=instructor_id)
        db.session.add(course)
        db.session.commit()
        
        flash('Course added successfully!', 'success')
        return redirect(url_for('courses'))
    
    instructors = Instructor.query.all()
    return render_template('add_course.html', instructors=instructors)

@app.route('/instructors')
def instructors():
    """List all instructors"""
    instructors = Instructor.query.all()
    return render_template('instructors.html', instructors=instructors)

@app.route('/instructors/add', methods=['GET', 'POST'])
def add_instructor():
    """Add a new instructor"""
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        
        instructor = Instructor(name=name, email=email)
        db.session.add(instructor)
        db.session.commit()
        
        flash('Instructor added successfully!', 'success')
        return redirect(url_for('instructors'))
    
    return render_template('add_instructor.html')

@app.route('/instructors/<int:instructor_id>/edit', methods=['GET', 'POST'])
def edit_instructor(instructor_id):
    """Edit an instructor"""
    instructor = Instructor.query.get_or_404(instructor_id)
    
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            
            # Check if email is changed and if it's already used by another instructor
            if email != instructor.email and Instructor.query.filter_by(email=email).first():
                flash('Email already exists for another instructor', 'danger')
                return render_template('edit_instructor.html', instructor=instructor)
            
            instructor.name = name
            instructor.email = email
            
            db.session.commit()
            flash(f'Instructor {name} updated successfully!', 'success')
            return redirect(url_for('instructors'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating instructor: {str(e)}', 'danger')
    
    return render_template('edit_instructor.html', instructor=instructor)

@app.route('/classrooms')
def classrooms():
    """List all classrooms"""
    classrooms = Classroom.query.all()
    return render_template('classrooms.html', classrooms=classrooms)

@app.route('/classrooms/add', methods=['GET', 'POST'])
def add_classroom():
    """Add a new classroom"""
    if request.method == 'POST':
        name = request.form['name']
        capacity = request.form['capacity']
        
        classroom = Classroom(name=name, capacity=capacity)
        db.session.add(classroom)
        db.session.commit()
        
        flash('Classroom added successfully!', 'success')
        return redirect(url_for('classrooms'))
    
    return render_template('add_classroom.html')

@app.route('/classrooms/<int:classroom_id>/edit', methods=['GET', 'POST'])
def edit_classroom(classroom_id):
    """Edit a classroom"""
    classroom = Classroom.query.get_or_404(classroom_id)
    
    if request.method == 'POST':
        try:
            name = request.form['name']
            capacity = request.form['capacity']
            
            # Check if name is changed and if it's already used by another classroom
            if name != classroom.name and Classroom.query.filter_by(name=name).first():
                flash('Classroom name already exists', 'danger')
                return render_template('edit_classroom.html', classroom=classroom)
            
            classroom.name = name
            classroom.capacity = capacity
            
            db.session.commit()
            flash(f'Classroom {name} updated successfully!', 'success')
            return redirect(url_for('classrooms'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating classroom: {str(e)}', 'danger')
    
    return render_template('edit_classroom.html', classroom=classroom)

@app.route('/timeslots')
def timeslots():
    """List all time slots"""
    timeslots = TimeSlot.query.all()
    return render_template('timeslots.html', timeslots=timeslots)

@app.route('/timeslots/add', methods=['GET', 'POST'])
def add_timeslot():
    """Add a new time slot"""
    if request.method == 'POST':
        try:
            day = request.form['day']
            start_time_str = request.form['start_time']
            end_time_str = request.form['end_time']
            
            # Convert string time to Python time objects
            from datetime import datetime, time
            
            # Parse time strings
            start_time_obj = datetime.strptime(start_time_str, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time_str, '%H:%M').time()
            
            timeslot = TimeSlot(day=day, start_time=start_time_obj, end_time=end_time_obj)
            db.session.add(timeslot)
            db.session.commit()
            
            flash('Time slot added successfully!', 'success')
            return redirect(url_for('timeslots'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding time slot: {str(e)}', 'danger')
            return redirect(url_for('add_timeslot'))
    
    return render_template('add_timeslot.html')

@app.route('/students')
def students():
    """List all students"""
    students = Student.query.all()
    return render_template('students.html', students=students)

@app.route('/students/add', methods=['GET', 'POST'])
def add_student():
    """Add a new student"""
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        
        student = Student(name=name, email=email)
        db.session.add(student)
        db.session.commit()
        
        flash('Student added successfully!', 'success')
        return redirect(url_for('students'))
    
    return render_template('add_student.html')

@app.route('/students/<int:student_id>/enroll', methods=['GET', 'POST'])
def enroll_student(student_id):
    """Enroll a student in courses"""
    student = Student.query.get_or_404(student_id)
    
    if request.method == 'POST':
        course_ids = request.form.getlist('courses')
        
        # Clear current enrollments
        student.courses = []
        
        # Add new enrollments
        for course_id in course_ids:
            course = Course.query.get(course_id)
            if course:
                student.courses.append(course)
        
        db.session.commit()
        flash('Student enrollment updated!', 'success')
        return redirect(url_for('students'))
    
    courses = Course.query.all()
    return render_template('enroll_student.html', student=student, courses=courses)

@app.route('/scheduler')
def scheduler_view():
    """View the scheduler page"""
    return render_template('scheduler.html')

@app.route('/scheduler/run', methods=['POST'])
def run_scheduler():
    """Run the timetable scheduler"""
    scheduler = TimetableScheduler()
    success, message = scheduler.run_scheduler()
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
        
    return redirect(url_for('timetable'))

@app.route('/timetable')
def timetable():
    """View the generated timetable"""
    courses = Course.query.all()
    timeslots = TimeSlot.query.all()
    classrooms = Classroom.query.all()
    
    return render_template('timetable.html', 
                          courses=courses, 
                          timeslots=timeslots, 
                          classrooms=classrooms)

@app.route('/graph')
def view_graph():
    """Visualize the conflict graph"""
    scheduler = TimetableScheduler()
    scheduler.load_data()
    scheduler.build_conflict_graph()
    
    G = scheduler.conflict_graph
    
    # Create a visualization of the graph
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_size=500, node_color='lightblue')
    
    # Draw edges with different colors based on weight
    edge_colors = ['gray' if G[u][v].get('weight', 1) == 1 else 'red' for u, v in G.edges()]
    nx.draw_networkx_edges(G, pos, width=2, edge_color=edge_colors)
    
    # Draw labels
    labels = {node: Course.query.get(node).code for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=10)
    
    # Save the plot to a BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    
    # Encode the image to base64
    graph_image = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    return render_template('graph.html', graph_image=graph_image)

@app.route('/reset_schedule', methods=['POST'])
def reset_schedule():
    """Reset all course schedules"""
    try:
        courses = Course.query.all()
        
        for course in courses:
            course.time_slot_id = None
            course.classroom_id = None
            course.color = None
        
        db.session.commit()
        flash('Schedule has been reset successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error resetting schedule: {str(e)}', 'danger')
    
    return redirect(url_for('timetable'))

@app.route('/courses/<int:course_id>/delete', methods=['POST'])
def delete_course(course_id):
    """Delete a course"""
    try:
        course = Course.query.get_or_404(course_id)
        
        # Remove the course from students' enrollments first
        for student in course.students.all():
            student.courses.remove(course)
        
        # Now delete the course
        db.session.delete(course)
        db.session.commit()
        flash(f'Course {course.code} deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting course: {str(e)}', 'danger')
    
    return redirect(url_for('courses'))

@app.route('/instructors/<int:instructor_id>/delete', methods=['POST'])
def delete_instructor(instructor_id):
    """Delete an instructor"""
    try:
        instructor = Instructor.query.get_or_404(instructor_id)
        
        # First check if instructor has any assigned courses
        if Course.query.filter_by(instructor_id=instructor.id).count() > 0:
            flash(f'Cannot delete instructor: {instructor.name} is still assigned to courses', 'danger')
            return redirect(url_for('instructors'))
        
        # Now delete the instructor
        db.session.delete(instructor)
        db.session.commit()
        flash(f'Instructor {instructor.name} deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting instructor: {str(e)}', 'danger')
    
    return redirect(url_for('instructors'))

@app.route('/classrooms/<int:classroom_id>/delete', methods=['POST'])
def delete_classroom(classroom_id):
    """Delete a classroom"""
    try:
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # First check if classroom is assigned to any courses
        if Course.query.filter_by(classroom_id=classroom.id).count() > 0:
            flash(f'Cannot delete classroom: {classroom.name} is still assigned to courses', 'danger')
            return redirect(url_for('classrooms'))
        
        # Now delete the classroom
        db.session.delete(classroom)
        db.session.commit()
        flash(f'Classroom {classroom.name} deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting classroom: {str(e)}', 'danger')
    
    return redirect(url_for('classrooms'))

@app.route('/timeslots/<int:timeslot_id>/delete', methods=['POST'])
def delete_timeslot(timeslot_id):
    """Delete a time slot"""
    try:
        timeslot = TimeSlot.query.get_or_404(timeslot_id)
        
        # First check if timeslot is assigned to any courses
        if Course.query.filter_by(time_slot_id=timeslot.id).count() > 0:
            flash(f'Cannot delete time slot: it is still assigned to courses', 'danger')
            return redirect(url_for('timeslots'))
        
        # Now delete the time slot
        db.session.delete(timeslot)
        db.session.commit()
        flash(f'Time slot deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting time slot: {str(e)}', 'danger')
    
    return redirect(url_for('timeslots'))

@app.route('/students/<int:student_id>/delete', methods=['POST'])
def delete_student(student_id):
    """Delete a student"""
    try:
        student = Student.query.get_or_404(student_id)
        
        # First clear the student's course enrollments
        student.courses = []
        
        # Now delete the student
        db.session.delete(student)
        db.session.commit()
        flash(f'Student {student.name} deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting student: {str(e)}', 'danger')
    
    return redirect(url_for('students'))

@app.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
def edit_student(student_id):
    """Edit a student"""
    student = Student.query.get_or_404(student_id)
    
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            
            # Check if email is changed and if it's already used by another student
            if email != student.email and Student.query.filter_by(email=email).first():
                flash('Email already exists for another student', 'danger')
                return render_template('edit_student.html', student=student)
            
            student.name = name
            student.email = email
            
            db.session.commit()
            flash(f'Student {name} updated successfully!', 'success')
            return redirect(url_for('students'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating student: {str(e)}', 'danger')
    
    return render_template('edit_student.html', student=student)

@app.route('/upload', methods=['POST'])
def upload_data():
    """Handle file uploads for bulk data import"""
    if 'fileUpload' not in request.files:
        flash('No file selected', 'danger')
        return redirect(request.referrer or url_for('index'))
    
    file = request.files['fileUpload']
    
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(request.referrer or url_for('index'))
    
    # Handle CSV files for data import
    if file.filename.lower().endswith('.csv'):
        data_type = request.form.get('dataType', '')
        if not data_type:
            flash('Please select a data type for CSV import', 'danger')
            return redirect(request.referrer or url_for('index'))
            
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'temp'), filename)
        file.save(file_path)
        
        try:
            if data_type == 'courses':
                import_courses(file_path)
            elif data_type == 'instructors':
                import_instructors(file_path)
            elif data_type == 'classrooms':
                import_classrooms(file_path)
            elif data_type == 'timeslots':
                import_timeslots(file_path)
            elif data_type == 'students':
                import_students(file_path)
            elif data_type == 'enrollments':
                import_enrollments(file_path)
            else:
                flash('Invalid data type selected', 'danger')
                return redirect(request.referrer or url_for('index'))
                
            flash(f'{data_type.capitalize()} data imported successfully!', 'success')
            
        except Exception as e:
            flash(f'Error importing data: {str(e)}', 'danger')
        
        # Clean up the temp file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Redirect to the appropriate page
        if data_type == 'courses':
            return redirect(url_for('courses'))
        elif data_type == 'instructors':
            return redirect(url_for('instructors'))
        elif data_type == 'classrooms':
            return redirect(url_for('classrooms'))
        elif data_type == 'timeslots':
            return redirect(url_for('timeslots'))
        elif data_type == 'students':
            return redirect(url_for('students'))
        elif data_type == 'enrollments':
            return redirect(url_for('students'))
    
    # Handle PDF uploads
    elif file.filename.lower().endswith('.pdf'):
        document_type = request.form.get('document_type', '')
        
        if not document_type:
            flash('Please select a document type for PDF uploads', 'danger')
            return redirect(request.referrer or url_for('index'))
            
        try:
            # Handle different document types
            if document_type == 'course_material':
                course_id = request.form.get('course_id')
                if not course_id:
                    flash('Please select a course for the course material', 'danger')
                    return redirect(request.referrer or url_for('index'))
                return handle_course_material_upload(file, course_id)
                
            elif document_type == 'syllabus':
                return handle_syllabus_upload(file)
                
            elif document_type == 'timetable':
                return handle_timetable_document_upload(file)
                
            elif document_type == 'schedule':
                return handle_timetable_document_upload(file)  # Uses same handler as timetable
                
            else:
                flash('Invalid document type selected', 'danger')
        except Exception as e:
            flash(f'Error uploading PDF: {str(e)}', 'danger')
        
        return redirect(request.referrer or url_for('index'))
    
    else:
        flash('Invalid file format. Please upload a CSV or PDF file.', 'danger')
    
    return redirect(request.referrer or url_for('index'))

def handle_course_material_upload(file, course_id):
    """Handle PDF upload as course material"""
    try:
        course = Course.query.get_or_404(course_id)
        
        # Create materials directory if it doesn't exist
        materials_dir = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'materials')
        if not os.path.exists(materials_dir):
            os.makedirs(materials_dir)
        
        # Create course-specific directory
        course_dir = os.path.join(materials_dir, f'course_{course.id}')
        if not os.path.exists(course_dir):
            os.makedirs(course_dir)
        
        # Save the file with a secure filename
        filename = secure_filename(file.filename)
        file_path = os.path.join(course_dir, filename)
        file.save(file_path)
        
        material_name = request.form.get('material_name', filename)
        flash(f'Course material "{material_name}" uploaded successfully!', 'success')
        return redirect(url_for('course_materials', course_id=course.id))
    except Exception as e:
        flash(f'Error uploading course material: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('index'))

def handle_syllabus_upload(file):
    """Handle PDF upload as a syllabus"""
    try:
        # Create syllabi directory if it doesn't exist
        syllabi_dir = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'syllabi')
        if not os.path.exists(syllabi_dir):
            os.makedirs(syllabi_dir)
        
        # Save the file with a secure filename
        filename = secure_filename(file.filename)
        file_path = os.path.join(syllabi_dir, filename)
        file.save(file_path)
        
        material_name = request.form.get('material_name', filename)
        flash(f'Syllabus "{material_name}" uploaded successfully!', 'success')
        return redirect(request.referrer or url_for('index'))
    except Exception as e:
        flash(f'Error uploading syllabus: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('index'))

def handle_timetable_document_upload(file):
    """Handle PDF upload as a timetable document"""
    try:
        # Create timetable_docs directory if it doesn't exist
        timetable_dir = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'timetable_docs')
        if not os.path.exists(timetable_dir):
            os.makedirs(timetable_dir)
        
        # Save the file with a secure filename
        filename = secure_filename(file.filename)
        file_path = os.path.join(timetable_dir, filename)
        file.save(file_path)
        
        material_name = request.form.get('material_name', filename)
        
        # If PDF contains timetable data, attempt to extract and apply it
        # This is a mock implementation since PDF text extraction would require additional libraries
        if "timetable" in filename.lower() or "schedule" in filename.lower():
            # In a real implementation, this would extract data from the PDF
            # For demonstration purposes, we'll just show a message about the feature
            flash(f'Timetable document "{material_name}" uploaded successfully! PDF parsing would extract scheduling information if implemented with libraries like PyPDF2 or pdfplumber.', 'info')
        else:
            flash(f'Timetable document "{material_name}" uploaded successfully!', 'success')
            
        return redirect(url_for('timetable'))
    except Exception as e:
        flash(f'Error uploading timetable document: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('index'))

def import_courses(file_path):
    """Import courses from a CSV file"""
    df = pd.read_csv(file_path)
    
    for _, row in df.iterrows():
        # Check if course already exists
        existing = Course.query.filter_by(code=row['code']).first()
        if not existing:
            # Get instructor if specified
            instructor_id = None
            if 'instructor_email' in row and row['instructor_email']:
                instructor = Instructor.query.filter_by(email=row['instructor_email']).first()
                if instructor:
                    instructor_id = instructor.id
            
            # Create new course
            course = Course(
                code=row['code'],
                name=row['name'],
                instructor_id=instructor_id
            )
            db.session.add(course)
    
    db.session.commit()

def import_instructors(file_path):
    """Import instructors from a CSV file"""
    df = pd.read_csv(file_path)
    
    for _, row in df.iterrows():
        # Check if instructor already exists
        existing = Instructor.query.filter_by(email=row['email']).first()
        if not existing:
            instructor = Instructor(
                name=row['name'],
                email=row['email']
            )
            db.session.add(instructor)
    
    db.session.commit()

def import_classrooms(file_path):
    """Import classrooms from a CSV file"""
    df = pd.read_csv(file_path)
    
    for _, row in df.iterrows():
        # Check if classroom already exists
        existing = Classroom.query.filter_by(name=row['name']).first()
        if not existing:
            classroom = Classroom(
                name=row['name'],
                capacity=row['capacity']
            )
            db.session.add(classroom)
    
    db.session.commit()

def import_timeslots(file_path):
    """Import time slots from a CSV file"""
    df = pd.read_csv(file_path)
    
    for _, row in df.iterrows():
        try:
            # Convert string time to Python time objects
            from datetime import datetime
            
            start_time_str = row['start_time']
            end_time_str = row['end_time']
            
            # Parse time strings
            start_time_obj = datetime.strptime(start_time_str, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time_str, '%H:%M').time()
            
            # Create new time slot
            timeslot = TimeSlot(
                day=row['day'],
                start_time=start_time_obj,
                end_time=end_time_obj
            )
            db.session.add(timeslot)
        except Exception as e:
            print(f"Error importing time slot: {e}")
            continue
    
    db.session.commit()

def import_students(file_path):
    """Import students from a CSV file"""
    df = pd.read_csv(file_path)
    
    for _, row in df.iterrows():
        # Check if student already exists
        existing = Student.query.filter_by(email=row['email']).first()
        if not existing:
            student = Student(
                name=row['name'],
                email=row['email']
            )
            db.session.add(student)
    
    db.session.commit()

def import_enrollments(file_path):
    """Import student enrollments from a CSV file"""
    df = pd.read_csv(file_path)
    
    for _, row in df.iterrows():
        try:
            student_id = row['student_id']
            course_id = row['course_id']
            
            student = Student.query.get(student_id)
            course = Course.query.get(course_id)
            
            if student and course:
                student.courses.append(course)
        except Exception as e:
            print(f"Error importing enrollment: {e}")
            continue
    
    db.session.commit()

def import_timetable(file_path):
    """Import a complete timetable from a CSV file with scheduling information"""
    df = pd.read_csv(file_path)
    success_count = 0
    error_count = 0
    
    for _, row in df.iterrows():
        try:
            # Get course by code
            course_code = row['Course Code']
            course = Course.query.filter_by(code=course_code).first()
            
            if not course:
                print(f"Course with code {course_code} not found")
                error_count += 1
                continue
                
            # Get or create instructor
            instructor_name = row['Instructor']
            if instructor_name and instructor_name != 'Not Assigned':
                instructor = Instructor.query.filter_by(name=instructor_name).first()
                if not instructor:
                    # Create new instructor
                    instructor = Instructor(name=instructor_name, email=f"{instructor_name.lower().replace(' ', '.')}@example.com")
                    db.session.add(instructor)
                    db.session.flush()  # Get ID without committing
                
                course.instructor_id = instructor.id
            
            # Get or create classroom
            classroom_name = row['Classroom']
            if classroom_name and classroom_name != 'Not Assigned':
                classroom = Classroom.query.filter_by(name=classroom_name).first()
                if not classroom:
                    # Create new classroom with default capacity of 30
                    classroom = Classroom(name=classroom_name, capacity=30)
                    db.session.add(classroom)
                    db.session.flush()  # Get ID without committing
                
                course.classroom_id = classroom.id
            
            # Get or create timeslot
            day = row['Day']
            time_str = row['Time']
            
            if day and day != 'Not Scheduled' and time_str and time_str != 'Not Scheduled':
                # Parse the time range (format: "HH:MM - HH:MM")
                time_parts = time_str.split(' - ')
                if len(time_parts) == 2:
                    start_time_str, end_time_str = time_parts
                    
                    from datetime import datetime
                    # Parse time strings
                    start_time_obj = datetime.strptime(start_time_str, '%H:%M').time()
                    end_time_obj = datetime.strptime(end_time_str, '%H:%M').time()
                    
                    # Look for existing timeslot
                    timeslot = TimeSlot.query.filter_by(
                        day=day,
                        start_time=start_time_obj,
                        end_time=end_time_obj
                    ).first()
                    
                    if not timeslot:
                        # Create new timeslot
                        timeslot = TimeSlot(
                            day=day,
                            start_time=start_time_obj,
                            end_time=end_time_obj
                        )
                        db.session.add(timeslot)
                        db.session.flush()  # Get ID without committing
                    
                    course.time_slot_id = timeslot.id
            
            success_count += 1
            
        except Exception as e:
            print(f"Error importing timetable row: {e}")
            error_count += 1
            continue
    
    db.session.commit()
    return success_count, error_count

@app.route('/export_timetable')
def export_timetable():
    """Export the timetable to a CSV file"""
    # Collect all scheduled courses
    courses = Course.query.filter(Course.time_slot_id.isnot(None)).all()
    
    if not courses:
        flash('No scheduled courses to export.', 'warning')
        return redirect(url_for('timetable'))
    
    # Create a StringIO object to write the CSV to
    output = StringIO()
    writer = csv.writer(output)
    
    # Write the header row
    writer.writerow(['Course Code', 'Course Name', 'Instructor', 'Day', 'Time', 'Classroom', 'Students'])
    
    # Write each scheduled course
    for course in courses:
        instructor_name = course.instructor.name if course.instructor else 'Not Assigned'
        day = course.time_slot.day if course.time_slot else 'Not Scheduled'
        time_range = f"{course.time_slot.start_time.strftime('%H:%M')} - {course.time_slot.end_time.strftime('%H:%M')}" if course.time_slot else 'Not Scheduled'
        classroom_name = course.classroom.name if course.classroom else 'Not Assigned'
        student_count = course.students.count()
        
        writer.writerow([
            course.code,
            course.name,
            instructor_name,
            day,
            time_range,
            classroom_name,
            student_count
        ])
    
    # Seek to the beginning of the StringIO object
    output.seek(0)
    
    # Create a response with the CSV data
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=timetable.csv'}
    )
    
    return response

@app.route('/import_timetable', methods=['POST'])
def import_timetable_route():
    """Import a complete timetable from a CSV file"""
    if 'timetableFile' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('timetable'))
    
    file = request.files['timetableFile']
    
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('timetable'))
    
    if not file.filename.lower().endswith('.csv'):
        flash('Only CSV files are supported for timetable import', 'danger')
        return redirect(url_for('timetable'))
    
    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), filename)
        file.save(file_path)
        
        success_count, error_count = import_timetable(file_path)
        
        # Clean up the temp file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        if error_count == 0:
            flash(f'Timetable imported successfully! {success_count} courses updated.', 'success')
        else:
            flash(f'Timetable imported with some issues. {success_count} courses updated, {error_count} errors.', 'warning')
        
    except Exception as e:
        flash(f'Error importing timetable: {str(e)}', 'danger')
    
    return redirect(url_for('timetable'))

@app.route('/conflicts')
def view_conflicts():
    """View detailed course conflicts"""
    scheduler = TimetableScheduler()
    conflicts = scheduler.get_conflict_details()
    
    # Group conflicts by type for better visualization
    student_conflicts = [c for c in conflicts if 'students' in c['type']]
    instructor_conflicts = [c for c in conflicts if 'instructor' in c['type']]
    
    # Get all courses for reference
    courses = Course.query.all()
    
    return render_template('conflicts.html', 
                          student_conflicts=student_conflicts,
                          instructor_conflicts=instructor_conflicts,
                          courses=courses,
                          total_conflicts=len(conflicts))

@app.route('/courses/<int:course_id>/assign', methods=['GET', 'POST'])
def assign_course(course_id):
    """Manually assign a course to a time slot and classroom"""
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        time_slot_id = request.form.get('time_slot_id')
        classroom_id = request.form.get('classroom_id')
        
        try:
            # Validate the assignment
            if time_slot_id and classroom_id:
                time_slot = TimeSlot.query.get(time_slot_id)
                classroom = Classroom.query.get(classroom_id)
                
                if not time_slot or not classroom:
                    flash('Invalid time slot or classroom selected', 'danger')
                    return redirect(url_for('assign_course', course_id=course.id))
                
                # Check for conflicts
                # 1. Instructor conflicts
                if course.instructor_id:
                    instructor_conflicts = Course.query.filter(
                        Course.instructor_id == course.instructor_id,
                        Course.time_slot_id == time_slot.id,
                        Course.id != course.id
                    ).count()
                    
                    if instructor_conflicts > 0:
                        flash('This instructor is already teaching another course during this time slot', 'danger')
                        return redirect(url_for('assign_course', course_id=course.id))
                
                # 2. Student conflicts
                student_conflicts = []
                for student in course.students.all():
                    for other_course in student.courses:
                        if other_course.id != course.id and other_course.time_slot_id == int(time_slot_id):
                            student_conflicts.append(student.name)
                            break
                
                if student_conflicts:
                    if len(student_conflicts) <= 3:
                        conflicts_text = ', '.join(student_conflicts)
                    else:
                        conflicts_text = f"{', '.join(student_conflicts[:3])} and {len(student_conflicts) - 3} others"
                    
                    flash(f'Warning: Students with conflicting schedules: {conflicts_text}', 'warning')
                
                # 3. Classroom conflicts
                classroom_conflicts = Course.query.filter(
                    Course.classroom_id == classroom.id,
                    Course.time_slot_id == time_slot.id,
                    Course.id != course.id
                ).count()
                
                if classroom_conflicts > 0:
                    flash('This classroom is already assigned to another course during this time slot', 'danger')
                    return redirect(url_for('assign_course', course_id=course.id))
                
                # 4. Check classroom capacity
                student_count = course.students.count()
                if student_count > classroom.capacity:
                    flash(f'Warning: The classroom capacity ({classroom.capacity}) is less than the number of students ({student_count})', 'warning')
                
                # Assign the course
                course.time_slot_id = time_slot.id
                course.classroom_id = classroom.id
                db.session.commit()
                
                flash(f'Course {course.code} has been assigned to {time_slot} in {classroom.name}', 'success')
                return redirect(url_for('timetable'))
            else:
                flash('Please select both a time slot and classroom', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error assigning course: {str(e)}', 'danger')
    
    # Get available time slots and classrooms
    time_slots = TimeSlot.query.all()
    classrooms = Classroom.query.all()
    
    return render_template('assign_course.html', 
                          course=course, 
                          time_slots=time_slots, 
                          classrooms=classrooms)

@app.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
def edit_course(course_id):
    """Edit a course"""
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        try:
            code = request.form['code']
            name = request.form['name']
            instructor_id = request.form.get('instructor_id')
            
            # Check if code is changed and if it's already used by another course
            if code != course.code and Course.query.filter_by(code=code).first():
                flash('Course code already exists', 'danger')
                instructors = Instructor.query.all()
                return render_template('edit_course.html', course=course, instructors=instructors)
            
            course.code = code
            course.name = name
            course.instructor_id = instructor_id if instructor_id else None
            
            db.session.commit()
            flash(f'Course {code} updated successfully!', 'success')
            return redirect(url_for('courses'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating course: {str(e)}', 'danger')
    
    instructors = Instructor.query.all()
    return render_template('edit_course.html', course=course, instructors=instructors)

@app.route('/courses/<int:course_id>/materials', methods=['GET', 'POST'])
def course_materials(course_id):
    """Manage course materials (PDF uploads)"""
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'material_file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)
            
        file = request.files['material_file']
        
        # If user does not select file, browser also
        # submits an empty part without filename
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename, ['pdf']):
            try:
                # Create materials directory if it doesn't exist
                materials_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'materials')
                if not os.path.exists(materials_dir):
                    os.makedirs(materials_dir)
                
                # Create course-specific directory
                course_dir = os.path.join(materials_dir, f'course_{course.id}')
                if not os.path.exists(course_dir):
                    os.makedirs(course_dir)
                
                # Save the file with a secure filename
                filename = secure_filename(file.filename)
                file_path = os.path.join(course_dir, filename)
                file.save(file_path)
                
                material_name = request.form.get('material_name', 'Unnamed Material')
                material_description = request.form.get('material_description', '')
                
                # Save in database (if implementing a CourseMaterial model)
                # For now, we'll just use the filesystem
                
                flash(f'Material "{material_name}" uploaded successfully', 'success')
                
            except Exception as e:
                flash(f'Error uploading file: {str(e)}', 'danger')
                
        else:
            flash('Invalid file format. Please upload a PDF file.', 'danger')
            
    # Get list of existing materials
    materials_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'materials', f'course_{course.id}')
    materials = []
    
    if os.path.exists(materials_dir):
        for filename in os.listdir(materials_dir):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(materials_dir, filename)
                size = os.path.getsize(file_path)
                mod_time = os.path.getmtime(file_path)
                materials.append({
                    'filename': filename,
                    'size': format_file_size(size),
                    'uploaded': datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M'),
                    'path': f'/uploads/materials/course_{course.id}/{filename}'
                })
    
    return render_template('course_materials.html', course=course, materials=materials)

@app.route('/uploads/<path:filename>')
def download_file(filename):
    """Download a file from the uploads directory"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

def allowed_file(filename, allowed_extensions):
    """Check if a file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def format_file_size(size_bytes):
    """Format file size in a human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1048576:
        return f"{(size_bytes / 1024):.1f} KB"
    else:
        return f"{(size_bytes / 1048576):.1f} MB"

@app.route('/courses/<int:course_id>/materials/<path:filename>/delete', methods=['POST'])
def delete_material(course_id, filename):
    """Delete a course material file"""
    try:
        course = Course.query.get_or_404(course_id)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'materials', f'course_{course.id}', filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            flash('Material deleted successfully', 'success')
        else:
            flash('File not found', 'danger')
            
    except Exception as e:
        flash(f'Error deleting file: {str(e)}', 'danger')
        
    return redirect(url_for('course_materials', course_id=course_id))

@app.route('/user_guide')
def user_guide():
    return render_template('user_guide.html')

@app.route('/quick_update', methods=['POST'])
def quick_update():
    """Handle quick updates from the dashboard"""
    update_type = request.form.get('update_type')
    item_id = request.form.get('item_id')
    
    if not update_type or not item_id:
        flash('Missing required parameters', 'danger')
        return redirect(url_for('index'))
    
    try:
        if update_type == 'course':
            course = Course.query.get_or_404(item_id)
            name = request.form.get('name')
            instructor_id = request.form.get('instructor_id')
            
            if name and name.strip():
                course.name = name
            
            if instructor_id:
                course.instructor_id = instructor_id
            
            db.session.commit()
            flash(f'Course {course.code} updated successfully!', 'success')
            
        elif update_type == 'instructor':
            instructor = Instructor.query.get_or_404(item_id)
            name = request.form.get('name')
            email = request.form.get('email')
            
            if name and name.strip():
                instructor.name = name
                
            if email and email.strip():
                # Check if email is already in use
                existing = Instructor.query.filter(Instructor.email == email, Instructor.id != instructor.id).first()
                if existing:
                    flash('Email is already in use by another instructor', 'danger')
                    return redirect(url_for('index'))
                instructor.email = email
            
            db.session.commit()
            flash(f'Instructor updated successfully!', 'success')
            
        elif update_type == 'classroom':
            classroom = Classroom.query.get_or_404(item_id)
            name = request.form.get('name')
            capacity = request.form.get('capacity')
            
            if name and name.strip():
                classroom.name = name
                
            if capacity and capacity.isdigit():
                classroom.capacity = int(capacity)
            
            db.session.commit()
            flash(f'Classroom updated successfully!', 'success')
            
        elif update_type == 'timeslot':
            timeslot = TimeSlot.query.get_or_404(item_id)
            day = request.form.get('day')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            
            if day and day.strip():
                timeslot.day = day
                
            if start_time and start_time.strip():
                # Convert string time to Python time object
                from datetime import datetime
                start_time_obj = datetime.strptime(start_time, '%H:%M').time()
                timeslot.start_time = start_time_obj
                
            if end_time and end_time.strip():
                # Convert string time to Python time object
                from datetime import datetime
                end_time_obj = datetime.strptime(end_time, '%H:%M').time()
                timeslot.end_time = end_time_obj
            
            db.session.commit()
            flash(f'Time slot updated successfully!', 'success')
            
        else:
            flash('Invalid update type', 'danger')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating: {str(e)}', 'danger')
        
    return redirect(url_for('index')) 