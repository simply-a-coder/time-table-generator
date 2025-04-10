import unittest
import networkx as nx
import sys
import os

# Add the parent directory to path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.controllers.scheduler import TimetableScheduler
from app import app, db
from app.models.models import Course, Instructor, Classroom, TimeSlot, Student

class TestTimetableScheduler(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        # Configure the app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        # Create all tables in a test database
        with app.app_context():
            db.create_all()
            self.create_test_data()
            
        # Initialize the scheduler
        self.scheduler = TimetableScheduler()
        
    def tearDown(self):
        """Clean up after each test"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def create_test_data(self):
        """Create sample data for testing"""
        # Create time slots
        time_slots = [
            TimeSlot(day='Monday', start_time='09:00', end_time='10:30'),
            TimeSlot(day='Monday', start_time='11:00', end_time='12:30'),
            TimeSlot(day='Tuesday', start_time='09:00', end_time='10:30'),
            TimeSlot(day='Tuesday', start_time='11:00', end_time='12:30')
        ]
        for ts in time_slots:
            db.session.add(ts)
        
        # Create classrooms
        classrooms = [
            Classroom(name='Room 101', capacity=30),
            Classroom(name='Room 102', capacity=50),
            Classroom(name='Room 103', capacity=100)
        ]
        for cr in classrooms:
            db.session.add(cr)
        
        # Create instructors
        instructors = [
            Instructor(name='Dr. Smith', email='smith@university.edu'),
            Instructor(name='Dr. Johnson', email='johnson@university.edu')
        ]
        for instr in instructors:
            db.session.add(instr)
        
        # Create courses
        courses = [
            Course(code='CS101', name='Introduction to Computer Science'),
            Course(code='CS102', name='Data Structures'),
            Course(code='MATH101', name='Calculus I'),
            Course(code='MATH102', name='Linear Algebra')
        ]
        for course in courses:
            db.session.add(course)
        
        # Create students
        students = [
            Student(name='Alice', email='alice@university.edu'),
            Student(name='Bob', email='bob@university.edu'),
            Student(name='Charlie', email='charlie@university.edu')
        ]
        for student in students:
            db.session.add(student)
        
        db.session.commit()
        
        # Assign instructors to courses
        courses[0].instructor_id = instructors[0].id  # CS101 -> Dr. Smith
        courses[1].instructor_id = instructors[0].id  # CS102 -> Dr. Smith
        courses[2].instructor_id = instructors[1].id  # MATH101 -> Dr. Johnson
        courses[3].instructor_id = instructors[1].id  # MATH102 -> Dr. Johnson
        
        # Enroll students in courses
        students[0].courses = [courses[0], courses[2]]  # Alice -> CS101, MATH101
        students[1].courses = [courses[0], courses[1], courses[2]]  # Bob -> CS101, CS102, MATH101
        students[2].courses = [courses[1], courses[3]]  # Charlie -> CS102, MATH102
        
        db.session.commit()
    
    def test_load_data(self):
        """Test that the scheduler correctly loads data from the database"""
        with app.app_context():
            self.scheduler.load_data()
            
            self.assertEqual(len(self.scheduler.courses), 4)
            self.assertEqual(len(self.scheduler.time_slots), 4)
            self.assertEqual(len(self.scheduler.rooms), 3)
    
    def test_build_conflict_graph(self):
        """Test that the conflict graph is correctly built"""
        with app.app_context():
            self.scheduler.load_data()
            self.scheduler.build_conflict_graph()
            
            # Check that the graph has the correct number of nodes
            self.assertEqual(len(self.scheduler.conflict_graph.nodes()), 4)
            
            # Check for conflicts:
            # CS101 and CS102 share an instructor (Dr. Smith) and a student (Bob)
            # CS101 and MATH101 share students (Alice, Bob)
            # CS102 and MATH102 share a student (Charlie)
            # MATH101 and MATH102 share an instructor (Dr. Johnson)
            
            # Get the course IDs
            cs101_id = Course.query.filter_by(code='CS101').first().id
            cs102_id = Course.query.filter_by(code='CS102').first().id
            math101_id = Course.query.filter_by(code='MATH101').first().id
            math102_id = Course.query.filter_by(code='MATH102').first().id
            
            # Check edges
            self.assertTrue(self.scheduler.conflict_graph.has_edge(cs101_id, cs102_id))
            self.assertTrue(self.scheduler.conflict_graph.has_edge(cs101_id, math101_id))
            self.assertTrue(self.scheduler.conflict_graph.has_edge(cs102_id, math102_id))
            self.assertTrue(self.scheduler.conflict_graph.has_edge(math101_id, math102_id))
    
    def test_greedy_coloring(self):
        """Test that the greedy coloring algorithm assigns valid colors"""
        with app.app_context():
            self.scheduler.load_data()
            self.scheduler.build_conflict_graph()
            colored_nodes, room_assignments = self.scheduler.greedy_coloring()
            
            # Check that all nodes have been colored
            self.assertEqual(len(colored_nodes), 4)
            
            # Check that adjacent nodes have different colors
            for u, v in self.scheduler.conflict_graph.edges():
                if colored_nodes[u] is not None and colored_nodes[v] is not None:
                    self.assertNotEqual(colored_nodes[u], colored_nodes[v])
            
            # Check that room assignments satisfy capacity constraints
            for course_id, room in room_assignments.items():
                course = Course.query.get(course_id)
                student_count = course.students.count()
                self.assertLessEqual(student_count, room.capacity)
    
    def test_apply_schedule(self):
        """Test that the schedule is correctly applied to the database"""
        with app.app_context():
            self.scheduler.load_data()
            self.scheduler.build_conflict_graph()
            colored_nodes, room_assignments = self.scheduler.greedy_coloring()
            
            # Apply the schedule
            self.scheduler.apply_schedule(colored_nodes, room_assignments)
            
            # Check that courses have been assigned time slots
            courses = Course.query.all()
            for course in courses:
                if course.id in colored_nodes and colored_nodes[course.id] is not None:
                    self.assertIsNotNone(course.time_slot_id)
                    self.assertIsNotNone(course.color)
                
                if course.id in room_assignments:
                    self.assertIsNotNone(course.classroom_id)

if __name__ == '__main__':
    unittest.main() 