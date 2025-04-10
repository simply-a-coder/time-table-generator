from app import db
from datetime import datetime

# Association tables for many-to-many relationships
course_student = db.Table('course_student',
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True),
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'), primary_key=True)
)

# Time slot model
class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(10), nullable=False)  # Monday, Tuesday, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    courses = db.relationship('Course', backref='time_slot', lazy=True)
    
    def __repr__(self):
        return f"{self.day} {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

# Classroom model
class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    courses = db.relationship('Course', backref='classroom', lazy=True)
    
    def __repr__(self):
        return f"{self.name} (Capacity: {self.capacity})"

# Instructor model
class Instructor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    courses = db.relationship('Course', backref='instructor', lazy=True)
    
    def __repr__(self):
        return self.name

# Student model
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    courses = db.relationship('Course', secondary=course_student, backref=db.backref('students', lazy='dynamic'))
    
    def __repr__(self):
        return self.name

# Course model
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('instructor.id'), nullable=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=True)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=True)
    color = db.Column(db.Integer, nullable=True)  # For graph coloring algorithm (represents assigned time slot)
    
    def __repr__(self):
        return f"{self.code}: {self.name}" 