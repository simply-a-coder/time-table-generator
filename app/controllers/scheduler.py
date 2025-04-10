import networkx as nx
from app.models.models import Course, TimeSlot, Classroom, Instructor
from app import db
import random

class TimetableScheduler:
    def __init__(self):
        self.conflict_graph = nx.Graph()
        self.courses = []
        self.time_slots = []
        self.rooms = []
        
    def load_data(self):
        """Load courses, time slots, and rooms from the database"""
        self.courses = Course.query.all()
        self.time_slots = TimeSlot.query.all()
        self.rooms = Classroom.query.all()
        
    def build_conflict_graph(self):
        """
        Build a graph where nodes are courses and edges represent conflicts
        Two courses conflict if they share students or instructors
        """
        # Clear the existing graph
        self.conflict_graph.clear()
        
        # Add all courses as nodes
        for course in self.courses:
            self.conflict_graph.add_node(course.id, course=course)
        
        # Add edges between courses that share students
        for i, course1 in enumerate(self.courses):
            for course2 in self.courses[i+1:]:
                # Check for student overlap (conflict)
                if course1.students.intersect(course2.students).count() > 0:
                    self.conflict_graph.add_edge(course1.id, course2.id, weight=1)
                    
                # Check for instructor conflict
                if course1.instructor_id == course2.instructor_id and course1.instructor_id is not None:
                    self.conflict_graph.add_edge(course1.id, course2.id, weight=2)
    
    def get_available_colors(self, node, colored_nodes):
        """
        Find available colors (time slots) for a node considering its neighbors
        """
        neighbors = list(self.conflict_graph.neighbors(node))
        used_colors = set()
        
        for neighbor in neighbors:
            if neighbor in colored_nodes and colored_nodes[neighbor] is not None:
                used_colors.add(colored_nodes[neighbor])
        
        all_colors = set(range(len(self.time_slots)))
        available_colors = list(all_colors - used_colors)
        
        return available_colors
    
    def find_suitable_room(self, course, time_slot, room_assignments):
        """
        Find a suitable room for a course based on student count and availability
        """
        student_count = course.students.count()
        
        # Get rooms available in this time slot
        available_rooms = list(self.rooms)
        
        # Remove rooms already assigned in this time slot
        for other_course in self.courses:
            if other_course.id != course.id and other_course.time_slot_id == time_slot.id:
                for rid, room in enumerate(available_rooms):
                    if other_course.classroom_id == room.id:
                        available_rooms.pop(rid)
                        break
        
        # Filter for rooms with sufficient capacity
        suitable_rooms = [r for r in available_rooms if r.capacity >= student_count]
        
        if not suitable_rooms:
            return None
            
        # Sort by capacity to find the best fit (minimize wasted capacity)
        suitable_rooms.sort(key=lambda r: r.capacity - student_count)
        
        # Return the room with the smallest sufficient capacity
        return suitable_rooms[0]
    
    def meets_constraints(self, course_id, color, room_assignments):
        """
        Check if assigning a color (time slot) to a course meets all constraints
        - Room capacity must be sufficient
        - Instructor must be available
        """
        course = Course.query.get(course_id)
        time_slot = self.time_slots[color]
        
        # Check instructor availability for this time slot
        if course.instructor_id:
            instructor_courses = Course.query.filter_by(instructor_id=course.instructor_id).all()
            for ic in instructor_courses:
                if ic.id != course_id and ic.time_slot_id == time_slot.id:
                    return False
                    
        # Find a suitable room
        room = self.find_suitable_room(course, time_slot, room_assignments)
        if not room:
            return False
            
        return True
    
    def greedy_coloring(self):
        """
        Implement the greedy graph coloring algorithm for scheduling
        """
        # Sort nodes by degree (most constrained first)
        nodes_by_degree = sorted(self.conflict_graph.nodes(), 
                                key=lambda x: self.conflict_graph.degree(x), 
                                reverse=True)
        
        colored_nodes = {}  # Maps node_id to color (time slot)
        room_assignments = {}  # Maps node_id to room
        
        for node in nodes_by_degree:
            available_colors = self.get_available_colors(node, colored_nodes)
            
            # Find a color that satisfies all constraints
            valid_color = None
            for color in available_colors:
                if self.meets_constraints(node, color, room_assignments):
                    valid_color = color
                    
                    # Assign a suitable room
                    course = Course.query.get(node)
                    time_slot = self.time_slots[color]
                    room = self.find_suitable_room(course, time_slot, room_assignments)
                    if room:
                        room_assignments[node] = room
                    
                    break
            
            # Assign the color to the node
            colored_nodes[node] = valid_color
        
        return colored_nodes, room_assignments
    
    def apply_schedule(self, colored_nodes, room_assignments):
        """
        Apply the computed schedule to the database
        """
        for course_id, color in colored_nodes.items():
            course = Course.query.get(course_id)
            
            if color is not None:
                # Assign time slot
                time_slot = self.time_slots[color]
                course.time_slot_id = time_slot.id
                course.color = color
                
                # Assign room
                if course_id in room_assignments:
                    course.classroom_id = room_assignments[course_id].id
            
        # Save changes to database
        db.session.commit()
    
    def run_scheduler(self):
        """
        Main method to run the scheduling process
        """
        try:
            # Check for minimum required data
            if Course.query.count() == 0:
                return False, "No courses found. Please add courses before scheduling."
                
            if TimeSlot.query.count() == 0:
                return False, "No time slots found. Please add time slots before scheduling."
                
            if Classroom.query.count() == 0:
                return False, "No classrooms found. Please add classrooms before scheduling."
            
            self.load_data()
            self.build_conflict_graph()
            
            if len(self.conflict_graph.nodes()) == 0:
                return False, "No courses to schedule."
                
            colored_nodes, room_assignments = self.greedy_coloring()
            
            # Check if all courses were assigned a time slot
            unscheduled = [course.code for course_id, color in colored_nodes.items() 
                          if color is None and Course.query.get(course_id)]
            
            if unscheduled:
                return False, f"Unable to schedule all courses. Unscheduled courses: {', '.join(unscheduled)}"
                
            self.apply_schedule(colored_nodes, room_assignments)
            return True, "Schedule generated successfully!"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Error generating schedule: {str(e)}"
    
    def get_conflict_details(self):
        """
        Get detailed information about conflicts between courses
        Returns a list of dictionaries with conflict information
        """
        conflicts = []
        
        # Build the graph if it hasn't been built yet
        if not self.conflict_graph.nodes():
            self.load_data()
            self.build_conflict_graph()
            
        # Analyze each edge (conflict)
        for course1_id, course2_id in self.conflict_graph.edges():
            course1 = Course.query.get(course1_id)
            course2 = Course.query.get(course2_id)
            
            if not course1 or not course2:
                continue
                
            # Determine conflict type
            conflict_type = []
            
            # Check for student overlap
            common_students = course1.students.intersect(course2.students).all()
            if common_students:
                conflict_type.append('students')
            
            # Check for instructor conflict
            if course1.instructor_id == course2.instructor_id and course1.instructor_id:
                conflict_type.append('instructor')
                
            # Get weight from graph (higher means stronger conflict)
            weight = self.conflict_graph[course1_id][course2_id].get('weight', 1)
            
            conflicts.append({
                'course1': {
                    'id': course1.id,
                    'code': course1.code,
                    'name': course1.name
                },
                'course2': {
                    'id': course2.id,
                    'code': course2.code,
                    'name': course2.name
                },
                'type': conflict_type,
                'weight': weight,
                'common_students': [{'id': s.id, 'name': s.name} for s in common_students] if 'students' in conflict_type else [],
                'instructor': {'id': course1.instructor.id, 'name': course1.instructor.name} if 'instructor' in conflict_type else None
            })
            
        return conflicts 