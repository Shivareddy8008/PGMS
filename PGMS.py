"""
═══════════════════════════════════════════════════════════════════════════════
    POLICE GRIEVANCE MANAGEMENT SYSTEM - ANDHRA PRADESH
    EPICS Project - Complete Production-Ready Implementation
    
    Features:
    ✓ Role-Based Authentication (Admin, Officer, Constable)
    ✓ Manual Case Entry with Auto-Categorization
    ✓ Bulk CSV Import with Progress Tracking
    ✓ Interactive Location Maps with Folium
    ✓ Crime Density Heatmaps
    ✓ Advanced Analytics Dashboard
    ✓ PDF Report Generation
    ✓ Case Assignment Workflow
    ✓ Activity Audit Logs
    ✓ Data Export Capabilities
    ✓ Search & Advanced Filtering
    ✓ User Management (Admin)
    ✓ AI Assistant (Optional - Ollama)
    
    Technology Stack:
    - Frontend: Streamlit
    - Database: MongoDB
    - Visualization: Plotly + Folium
    - Geolocation: GeoPy
    - PDF: ReportLab
    - AI: Ollama (Optional)
    
═══════════════════════════════════════════════════════════════════════════════
"""

import streamlit as st
import pandas as pd
import numpy as np
from pymongo import MongoClient
from datetime import datetime, timedelta
import bcrypt
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import os
import chardet
import requests
import json
from bson import ObjectId
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import warnings
warnings.filterwarnings('ignore')


# ═══════════════════════════════════════════════════════════════════════════
#                           CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

class Config:
    """System configuration and constants"""
    
    # Database
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    DATABASE_NAME = os.getenv('DB_NAME', 'ap_police_grievance_system')
    
    # AI Integration
    OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    
    # Organization Details
    COMPANY_NAME = "Police Grievance Management System"
    POLICE_STATION = "Andhra Pradesh Police Department"
    DEPARTMENT_LOGO = "🚔"  # Use emoji or provide logo path
    
    # User Roles
    ROLE_ADMIN = "admin"
    ROLE_OFFICER = "superior_officer"
    ROLE_CONSTABLE = "constable"
    
    # Complaint Categories
    CATEGORIES = [
        "Land Dispute", "Domestic Violence", "Theft", "Traffic Violation",
        "Property Dispute", "Assault", "Fraud", "Harassment", "Cheque Bounce",
        "Missing Person", "Cyber Crime", "Robbery", "Drugs", "Corruption",
        "Vandalism", "Sexual Assault", "Murder", "Kidnapping", "Other"
    ]
    
    # Status Options
    STATUS_OPTIONS = ["Open", "In Progress", "Resolved", "Closed"]
    
    # Priority Levels
    PRIORITY_LEVELS = ["Low", "Medium", "High", "Critical"]
    
    # Color Schemes
    PRIORITY_COLORS = {
        'Critical': '#e74c3c',  # Red
        'High': '#f39c12',      # Orange
        'Medium': '#f1c40f',    # Yellow
        'Low': '#27ae60'        # Green
    }
    
    STATUS_COLORS = {
        'Open': '#ff6b6b',
        'In Progress': '#feca57',
        'Resolved': '#48cae4',
        'Closed': '#06ffa5'
    }


# ═══════════════════════════════════════════════════════════════════════════
#                         DATABASE MANAGER
# ═══════════════════════════════════════════════════════════════════════════

class DatabaseManager:
    """Handle all database operations with MongoDB"""
    
    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
        self.db = self.client[Config.DATABASE_NAME]
        self.grievances = self.db.grievances
        self.users = self.db.users
        self.activity_logs = self.db.activity_logs
        self.assignments = self.db.assignments
        
        self.create_indexes()
        self.init_default_users()
    
    def create_indexes(self):
        """Create database indexes for performance optimization"""
        try:
            self.grievances.create_index([("case_number", 1)], unique=True)
            self.grievances.create_index([("status", 1)])
            self.grievances.create_index([("category", 1)])
            self.grievances.create_index([("priority", 1)])
            self.grievances.create_index([("created_at", -1)])
            self.grievances.create_index([("submitted_by_id", 1)])
            self.grievances.create_index([("district", 1)])
            self.users.create_index([("username", 1)], unique=True)
            self.users.create_index([("badge_number", 1)], unique=True)
            self.activity_logs.create_index([("timestamp", -1)])
        except Exception as e:
            print(f"Index creation warning: {e}")
    
    def init_default_users(self):
        """Initialize default system users"""
        default_users = [
            {
                "username": "admin",
                "password": "admin@2025",
                "role": Config.ROLE_ADMIN,
                "full_name": "System Administrator",
                "badge_number": "ADMIN001",
                "station": "Headquarters",
                "email": "admin@appolice.gov.in"
            },
            {
                "username": "officer1",
                "password": "officer@2025",
                "role": Config.ROLE_OFFICER,
                "full_name": "Senior Police Inspector",
                "badge_number": "SI001",
                "station": "Vijayawada Central",
                "email": "officer1@appolice.gov.in"
            },
            {
                "username": "constable1",
                "password": "constable@2025",
                "role": Config.ROLE_CONSTABLE,
                "full_name": "Police Constable - Data Entry",
                "badge_number": "PC001",
                "station": "Vijayawada Central",
                "email": "constable1@appolice.gov.in"
            }
        ]
        
        for user_data in default_users:
            if not self.users.find_one({"username": user_data["username"]}):
                hashed_password = bcrypt.hashpw(user_data["password"].encode('utf-8'), bcrypt.gensalt())
                user_data["password"] = hashed_password
                user_data["created_at"] = datetime.now()
                user_data["is_active"] = True
                user_data["last_login"] = None
                self.users.insert_one(user_data)
    
    def authenticate_user(self, username, password):
        """Authenticate user and update last login"""
        user = self.users.find_one({"username": username, "is_active": True})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            # Update last login
            self.users.update_one(
                {"_id": user['_id']},
                {"$set": {"last_login": datetime.now()}}
            )
            
            self.log_activity(
                user_id=str(user['_id']),
                username=username,
                action="login",
                details="User logged in successfully"
            )
            return user
        return None
    
    def create_user(self, username, password, role, full_name, badge_number, station, email=""):
        """Create new user with validation"""
        if self.users.find_one({"username": username}):
            return False, "Username already exists"
        
        if self.users.find_one({"badge_number": badge_number}):
            return False, "Badge number already exists"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.users.insert_one({
            "username": username,
            "password": hashed_password,
            "role": role,
            "full_name": full_name,
            "badge_number": badge_number,
            "station": station,
            "email": email,
            "created_at": datetime.now(),
            "is_active": True,
            "last_login": None
        })
        return True, "User created successfully"
    
    def insert_grievance(self, grievance_data):
        """Insert new grievance with validation"""
        grievance_data['created_at'] = datetime.now()
        grievance_data['updated_at'] = datetime.now()
        grievance_data['case_number'] = self.generate_case_number()
        grievance_data['status_history'] = [{
            'status': grievance_data['status'],
            'updated_by': grievance_data.get('submitted_by', 'System'),
            'updated_at': datetime.now(),
            'remarks': 'Case registered'
        }]
        
        result = self.grievances.insert_one(grievance_data)
        
        self.log_activity(
            user_id=grievance_data.get('submitted_by_id', 'system'),
            username=grievance_data.get('submitted_by', 'System'),
            action="create_grievance",
            details=f"Created case: {grievance_data['case_number']}"
        )
        
        return result
    
    def generate_case_number(self):
        """Generate unique case number with year prefix"""
        year = datetime.now().year
        # Get count of cases for current year
        count = self.grievances.count_documents({
            "case_number": {"$regex": f"^FIR-{year}"}
        }) + 1
        return f"FIR-{year}-{count:06d}"
    
    def get_all_grievances(self, user_role=None, user_id=None, filters=None):
        """Get grievances with role-based access and optional filters"""
        query = {}
        
        # Role-based filtering
        if user_role == Config.ROLE_CONSTABLE:
            query["submitted_by_id"] = user_id
        
        # Apply additional filters
        if filters:
            if filters.get('status') and filters['status'] != 'All':
                query['status'] = filters['status']
            if filters.get('category') and filters['category'] != 'All':
                query['category'] = filters['category']
            if filters.get('priority') and filters['priority'] != 'All':
                query['priority'] = filters['priority']
            if filters.get('district') and filters['district'] != 'All':
                query['district'] = filters['district']
            if filters.get('date_from'):
                query['created_at'] = {'$gte': filters['date_from']}
            if filters.get('date_to'):
                if 'created_at' in query:
                    query['created_at']['$lte'] = filters['date_to']
                else:
                    query['created_at'] = {'$lte': filters['date_to']}
        
        return list(self.grievances.find(query).sort("created_at", -1))
    
    def update_grievance(self, grievance_id, update_data, user_id, username):
        """Update grievance with history tracking"""
        update_data['updated_at'] = datetime.now()
        update_data['last_updated_by'] = username
        
        # Track status changes
        if 'status' in update_data:
            grievance = self.grievances.find_one({"_id": ObjectId(grievance_id)})
            if grievance:
                status_history = grievance.get('status_history', [])
                status_history.append({
                    'status': update_data['status'],
                    'updated_by': username,
                    'updated_at': datetime.now(),
                    'remarks': update_data.get('remarks', '')
                })
                update_data['status_history'] = status_history
        
        result = self.grievances.update_one(
            {"_id": ObjectId(grievance_id)},
            {"$set": update_data}
        )
        
        self.log_activity(
            user_id=user_id,
            username=username,
            action="update_grievance",
            details=f"Updated case: {grievance_id}"
        )
        
        return result
    
    def bulk_update_status(self, case_ids, new_status, user_id, username):
        """Bulk update status for multiple cases"""
        updated_count = 0
        for case_id in case_ids:
            try:
                self.update_grievance(
                    case_id,
                    {"status": new_status, "remarks": f"Bulk updated to {new_status}"},
                    user_id,
                    username
                )
                updated_count += 1
            except:
                continue
        return updated_count
    
    def assign_case(self, case_id, assigned_to_username, assigned_by_id, assigned_by_name):
        """Assign case to an officer"""
        assigned_to = self.users.find_one({"username": assigned_to_username})
        if not assigned_to:
            return False, "User not found"
        
        assignment = {
            "case_id": case_id,
            "assigned_to": assigned_to_username,
            "assigned_to_name": assigned_to['full_name'],
            "assigned_by": assigned_by_name,
            "assigned_by_id": assigned_by_id,
            "assigned_at": datetime.now(),
            "status": "active"
        }
        
        self.assignments.insert_one(assignment)
        
        self.grievances.update_one(
            {"_id": ObjectId(case_id)},
            {"$set": {
                "assigned_to": assigned_to_username,
                "assigned_to_name": assigned_to['full_name'],
                "assigned_at": datetime.now()
            }}
        )
        
        self.log_activity(
            user_id=assigned_by_id,
            username=assigned_by_name,
            action="assign_case",
            details=f"Assigned case to {assigned_to_username}"
        )
        
        return True, "Case assigned successfully"
    
    def log_activity(self, user_id, username, action, details):
        """Log user activity for audit trail"""
        self.activity_logs.insert_one({
            "user_id": user_id,
            "username": username,
            "action": action,
            "details": details,
            "timestamp": datetime.now(),
            "ip_address": "localhost"  # Can be enhanced with actual IP tracking
        })
    
    def get_activity_logs(self, limit=100, filters=None):
        """Get activity logs with optional filtering"""
        query = {}
        if filters:
            if filters.get('username'):
                query['username'] = filters['username']
            if filters.get('action'):
                query['action'] = filters['action']
            if filters.get('date_from'):
                query['timestamp'] = {'$gte': filters['date_from']}
        
        return list(self.activity_logs.find(query).sort("timestamp", -1).limit(limit))
    
    def get_all_users(self, active_only=True):
        """Get all users with optional active filter"""
        query = {"is_active": True} if active_only else {}
        return list(self.users.find(query).sort("created_at", -1))
    
    def get_statistics(self, user_role=None, user_id=None):
        """Get comprehensive system statistics"""
        grievances = self.get_all_grievances(user_role, user_id)
        df = pd.DataFrame(grievances) if grievances else pd.DataFrame()
        
        stats = {
            'total_cases': len(grievances),
            'open_cases': len(df[df['status'] == 'Open']) if not df.empty else 0,
            'in_progress': len(df[df['status'] == 'In Progress']) if not df.empty else 0,
            'resolved_cases': len(df[df['status'] == 'Resolved']) if not df.empty else 0,
            'closed_cases': len(df[df['status'] == 'Closed']) if not df.empty else 0,
            'critical_cases': len(df[df['priority'] == 'Critical']) if not df.empty else 0,
            'resolution_rate': 0,
            'avg_resolution_time': 0
        }
        
        if stats['total_cases'] > 0:
            stats['resolution_rate'] = (stats['resolved_cases'] / stats['total_cases']) * 100
        
        return stats


# ═══════════════════════════════════════════════════════════════════════════
#                         TEXT PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════

class TextProcessor:
    """Handle text processing and categorization"""
    
    def categorize_grievance(self, text):
        """Auto-categorize grievance based on keywords with Telugu support"""
        text_lower = text.lower()
        
        category_keywords = {
            'Land Dispute': ['land', 'property dispute', 'boundary', 'encroachment', 'ancestral property', 'survey', 'acre', 'hectare', 'భూమి', 'సర్వే'],
            'Domestic Violence': ['domestic violence', 'family violence', 'spouse', 'dowry', 'wife', 'husband', 'dowry harassment', 'దుర్భాసలు', 'కట్నం'],
            'Theft': ['theft', 'stolen', 'burglary', 'break-in', 'shoplifting', 'pickpocket', 'చోరీ', 'దొంగతనం'],
            'Traffic Violation': ['traffic', 'speeding', 'rash driving', 'accident', 'hit and run', 'drunk driving', 'triple riding', 'రోడ్డు ప్రమాదం'],
            'Property Dispute': ['property dispute', 'real estate', 'construction dispute', 'illegal construction', 'స్థలం వివాదం'],
            'Assault': ['assault', 'attack', 'beating', 'violence', 'fight', 'hurt', 'injured', 'దెబ్బలు', 'కొట్టారు'],
            'Fraud': ['fraud', 'scam', 'cheating', 'forgery', 'embezzlement', 'fake', 'duplicate', 'మోసం', 'బూటకం'],
            'Harassment': ['harassment', 'stalking', 'threatening', 'intimidation', 'bullying', 'eve teasing', 'వేధింపులు'],
            'Cheque Bounce': ['cheque bounce', 'dishonored cheque', 'bounced cheque', 'insufficient funds', 'చెక్కు బౌన్స్'],
            'Missing Person': ['missing', 'disappeared', 'lost person', 'runaway', 'absconding', 'కనుగొనలేదు', 'తప్పిపోయారు'],
            'Cyber Crime': ['cyber', 'online fraud', 'internet', 'hacking', 'phishing', 'email scam', 'digital fraud', 'upi fraud'],
            'Robbery': ['robbery', 'mugging', 'armed robbery', 'looting', 'dacoity', 'snatching', 'chain snatching'],
            'Drugs': ['drugs', 'narcotics', 'substance', 'ganja', 'cannabis', 'illegal substance', 'డ్రగ్స్'],
            'Corruption': ['corruption', 'bribery', 'bribe', 'illegal payment', 'extortion', 'లంచం'],
            'Vandalism': ['vandalism', 'property damage', 'graffiti', 'destruction', 'విధ్వంసం'],
            'Sexual Assault': ['sexual assault', 'rape', 'molestation', 'sexual harassment', 'లైంగిక వేధింపులు'],
            'Murder': ['murder', 'killing', 'homicide', 'death', 'killed', 'హత్య'],
            'Kidnapping': ['kidnapping', 'abduction', 'kidnap', 'forceful detention', 'అపహరణ']
        }
        
        # Score each category
        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score, or 'Other' if no matches
        if category_scores:
            return max(category_scores, key=category_scores.get)
        return 'Other'
    
    def extract_priority_indicators(self, text, category):
        """Suggest priority based on text analysis"""
        text_lower = text.lower()
        
        critical_keywords = ['murder', 'rape', 'kidnap', 'armed', 'weapon', 'death', 'critical', 'emergency', 'urgent']
        high_keywords = ['assault', 'robbery', 'threat', 'violence', 'missing', 'abduction']
        
        if any(keyword in text_lower for keyword in critical_keywords):
            return 'Critical'
        elif any(keyword in text_lower for keyword in high_keywords):
            return 'High'
        elif category in ['Murder', 'Sexual Assault', 'Kidnapping']:
            return 'Critical'
        elif category in ['Robbery', 'Assault', 'Missing Person']:
            return 'High'
        else:
            return 'Medium'


# ═══════════════════════════════════════════════════════════════════════════
#                         LOCATION GEOCODER
# ═══════════════════════════════════════════════════════════════════════════

class LocationGeocoder:
    """Handle location geocoding with caching"""
    
    def __init__(self):
        self.geolocator = Nominatim(user_agent="ap_police_grievance_v2", timeout=10)
        self.ap_center = [15.9129, 79.7400]
        self.cache = {}
    
    def get_ap_districts_coordinates(self):
        """Predefined coordinates for AP locations"""
        return {
            'Vijayawada': (16.5062, 80.6480),
            'Visakhapatnam': (17.6868, 83.2185),
            'Guntur': (16.3067, 80.4365),
            'Tirupati': (13.6288, 79.4192),
            'Anantapur': (14.6819, 77.6006),
            'Kurnool': (15.8281, 78.0373),
            'Nellore': (14.4426, 79.9865),
            'Kadapa': (14.4673, 78.8242),
            'Rajahmundry': (17.0005, 81.8040),
            'Kakinada': (16.9891, 82.2475),
            'Eluru': (16.7107, 81.0952),
            'Ongole': (15.5057, 80.0499),
            'Chittoor': (13.2172, 79.1003),
            'Vizianagaram': (18.1167, 83.4000),
            'Srikakulam': (18.2949, 83.8938),
            'Krishna': (16.5062, 80.6480),
            'East Godavari': (17.0005, 81.8040),
            'West Godavari': (16.7107, 81.0952),
            'Prakasam': (15.5057, 80.0499)
        }
    
    def geocode_location(self, location_string):
        """Convert location to coordinates with caching"""
        if not location_string or location_string.strip() == "" or location_string == "Not specified":
            return None
        
        # Check cache first
        if location_string in self.cache:
            return self.cache[location_string]
        
        # Check predefined districts
        districts = self.get_ap_districts_coordinates()
        for district, coords in districts.items():
            if district.lower() in location_string.lower():
                self.cache[location_string] = coords
                return coords
        
        # Try geocoding
        try:
            full_location = f"{location_string}, Andhra Pradesh, India"
            location = self.geolocator.geocode(full_location, timeout=10)
            
            if location:
                coords = (location.latitude, location.longitude)
                self.cache[location_string] = coords
                return coords
        except (GeocoderTimedOut, Exception) as e:
            print(f"Geocoding error: {e}")
        
        return None


# ═══════════════════════════════════════════════════════════════════════════
#                         CSV PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════

class CSVProcessor:
    """Handle CSV file processing with validation"""
    
    @staticmethod
    def detect_encoding(file_bytes):
        """Detect file encoding"""
        result = chardet.detect(file_bytes)
        return result['encoding'] or 'utf-8'
    
    @staticmethod
    def process_csv_file(uploaded_file):
        """Process uploaded CSV with error handling"""
        try:
            file_bytes = uploaded_file.read()
            encoding = CSVProcessor.detect_encoding(file_bytes)
            uploaded_file.seek(0)
            
            df = pd.read_csv(uploaded_file, encoding=encoding)
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            return df, None
        except Exception as e:
            return None, f"Error reading CSV: {str(e)}"
    
    @staticmethod
    def validate_csv_structure(df):
        """Validate CSV has required columns"""
        required_columns = ['title', 'description']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"
        
        # Check for empty dataframe
        if len(df) == 0:
            return False, "CSV file is empty"
        
        return True, "CSV structure is valid"
    
    @staticmethod
    def export_to_csv(data, filename="export.csv"):
        """Export data to CSV"""
        try:
            df = pd.DataFrame(data)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            return csv_buffer.getvalue()
        except Exception as e:
            return None


# ═══════════════════════════════════════════════════════════════════════════
#                         PDF REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

class PDFReportGenerator:
    """Generate comprehensive PDF reports"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._add_custom_styles()
    
    def _add_custom_styles(self):
        """Add custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
    
    def create_grievance_report(self, grievances, stats=None, include_charts=False):
        """Create comprehensive PDF report"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch)
        story = []
        
        # Title Section
        story.append(Paragraph(
            f"{Config.POLICE_STATION}<br/>{Config.COMPANY_NAME}<br/>Official Report",
            self.styles['CustomTitle']
        ))
        story.append(Spacer(1, 0.3*inch))
        
        # Report Metadata
        report_date = datetime.now().strftime('%d %B %Y, %I:%M %p')
        metadata = [
            ['Report Generated:', report_date],
            ['Total Cases in Report:', str(len(grievances))],
            ['Report Type:', 'Comprehensive Analysis'],
            ['Status:', 'Official Document']
        ]
        
        meta_table = Table(metadata, colWidths=[2.5*inch, 3.5*inch])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7'))
        ]))
        
        story.append(meta_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Statistics Summary
        if stats:
            story.append(Paragraph("Case Statistics Summary", self.styles['CustomHeading']))
            
            stats_data = [
                ['Metric', 'Count', 'Percentage'],
                ['Total Cases', str(stats['total_cases']), '100%'],
                ['Open Cases', str(stats['open_cases']), f"{(stats['open_cases']/max(stats['total_cases'],1)*100):.1f}%"],
                ['In Progress', str(stats['in_progress']), f"{(stats['in_progress']/max(stats['total_cases'],1)*100):.1f}%"],
                ['Resolved Cases', str(stats['resolved_cases']), f"{(stats['resolved_cases']/max(stats['total_cases'],1)*100):.1f}%"],
                ['Critical Priority', str(stats['critical_cases']), f"{(stats['critical_cases']/max(stats['total_cases'],1)*100):.1f}%"],
            ]
            
            stats_table = Table(stats_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7'))
            ]))
            
            story.append(stats_table)
            story.append(Spacer(1, 0.2*inch))
        
        # Cases Detail
        if grievances:
            story.append(Paragraph("Detailed Case Information", self.styles['CustomHeading']))
            story.append(Spacer(1, 0.1*inch))
            
            # Limit to first 100 cases for PDF size
            display_grievances = grievances[:100]
            
            table_data = [['Case No.', 'Title', 'Category', 'Status', 'Priority', 'Date']]
            
            for grievance in display_grievances:
                title = str(grievance.get('title', ''))[:40]
                if len(str(grievance.get('title', ''))) > 40:
                    title += '...'
                
                created_date = grievance.get('created_at', datetime.now())
                if isinstance(created_date, datetime):
                    date_str = created_date.strftime('%d-%m-%Y')
                else:
                    date_str = str(created_date)[:10]
                
                row = [
                    grievance.get('case_number', 'N/A'),
                    title,
                    grievance.get('category', 'Other'),
                    grievance.get('status', 'Open'),
                    grievance.get('priority', 'Medium'),
                    date_str
                ]
                table_data.append(row)
            
            cases_table = Table(table_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 1*inch, 0.8*inch, 0.8*inch])
            cases_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
            ]))
            
            story.append(cases_table)
            
            if len(grievances) > 100:
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph(
                    f"Note: Showing first 100 cases. Total cases: {len(grievances)}",
                    self.styles['Normal']
                ))
        
        # Footer
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(
            "─" * 80,
            self.styles['Normal']
        ))
        story.append(Paragraph(
            f"This is an official computer-generated report from {Config.POLICE_STATION}<br/>"
            f"Generated on: {report_date}<br/>"
            f"Confidential Document - For Official Use Only",
            ParagraphStyle('Footer', parent=self.styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        ))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer


# ═══════════════════════════════════════════════════════════════════════════
#                         OLLAMA AI INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════

class OllamaAI:
    """AI assistant integration (optional)"""
    
    def __init__(self):
        self.base_url = Config.OLLAMA_URL
    
    def check_connection(self):
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self):
        """Get list of available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
            return []
        except:
            return []
    
    def generate_response(self, prompt, model="llama2", context=""):
        """Generate AI response"""
        try:
            payload = {
                "model": model,
                "prompt": f"Context: {context}\n\nQuestion: {prompt}\n\nProvide a helpful, professional answer:",
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('response', 'No response generated')
            return f"Error: Status code {response.status_code}"
        except requests.exceptions.Timeout:
            return "Request timed out. The AI is taking too long to respond."
        except Exception as e:
            return f"Error: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════
#                    MAIN APPLICATION CLASS
# ═══════════════════════════════════════════════════════════════════════════

class PoliceGrievanceApp:
    """Main Streamlit application"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.text_processor = TextProcessor()
        self.csv_processor = CSVProcessor()
        self.pdf_generator = PDFReportGenerator()
        self.geocoder = LocationGeocoder()
        self.ai = OllamaAI()
        
        # Initialize session state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
    
    def authenticate(self):
        """Authentication page with improved UI"""
        st.markdown(f"<h1 style='text-align: center;'>{Config.DEPARTMENT_LOGO} {Config.COMPANY_NAME}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center; color: #7f8c8d;'>{Config.POLICE_STATION}</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("### 🔐 Secure Login Portal")
            
            with st.form("login_form"):
                username = st.text_input("👤 Username", placeholder="Enter your username")
                password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
                
                submitted = st.form_submit_button("🔓 Login", use_container_width=True, type="primary")
                
                if submitted:
                    if not username or not password:
                        st.error("❌ Please enter both username and password")
                    else:
                        user = self.db.authenticate_user(username, password)
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user = user
                            st.success(f"✅ Welcome, {user['full_name']}!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Invalid credentials. Please try again.")
            
            st.markdown("---")
            
            with st.expander("📋 Demo Login Credentials"):
                st.warning("⚠️ **Important:** Change these passwords before production deployment!")
                st.info("""
                **Administrator:**
                - Username: `admin`
                - Password: `admin@2025`
                
                **Police Officer:**
                - Username: `officer1`
                - Password: `officer@2025`
                
                **Constable:**
                - Username: `constable1`
                - Password: `constable@2025`
                """)
    
    def sidebar(self):
        """Enhanced sidebar with role-based navigation"""
        st.sidebar.markdown(f"<h2 style='text-align: center;'>{Config.DEPARTMENT_LOGO} Navigation</h2>", unsafe_allow_html=True)
        st.sidebar.markdown("---")
        
        if st.session_state.get('user'):
            user = st.session_state.user
            
            # User info card
            st.sidebar.success(f"**{user['full_name']}**")
            st.sidebar.info(f"🎖️ {user['role'].replace('_', ' ').title()}")
            st.sidebar.caption(f"📛 Badge: {user['badge_number']}")
            st.sidebar.caption(f"🏢 Station: {user['station']}")
            
            if user.get('last_login'):
                st.sidebar.caption(f"🕐 Last Login: {user['last_login'].strftime('%d-%m-%Y %H:%M')}")
            
            st.sidebar.markdown("---")
        
        role = st.session_state.user.get('role')
        
        # Role-based navigation
        if role == Config.ROLE_ADMIN:
            navigation_options = [
                "📊 Dashboard",
                "👥 User Management",
                "📋 All Cases",
                "✍️ Manual Entry",
                "📁 CSV Import",
                "📈 Analytics",
                "🗺️ Location Map",
                "🔥 Crime Heatmap",
                "🎯 Case Assignment",
                "📜 Activity Logs",
                "📄 Generate Reports",
                "📤 Export Data",
                "🤖 AI Assistant"
            ]
        elif role == Config.ROLE_OFFICER:
            navigation_options = [
                "📊 Dashboard",
                "📋 All Cases",
                "✍️ Manual Entry",
                "📁 CSV Import",
                "📈 Analytics",
                "🗺️ Location Map",
                "🔥 Crime Heatmap",
                "🎯 Case Assignment",
                "📄 Generate Reports",
                "📤 Export Data",
                "🤖 AI Assistant"
            ]
        else:  # Constable
            navigation_options = [
                "📊 My Dashboard",
                "📋 My Cases",
                "✍️ Manual Entry",
                "📁 CSV Import",
                "🗺️ My Cases Map",
                "📄 My Reports",
                "📤 Export My Data"
            ]
        
        choice = st.sidebar.radio("**Navigate to:**", navigation_options, label_visibility="collapsed")
        
        st.sidebar.markdown("---")
        
        # System info
        with st.sidebar.expander("ℹ️ System Information"):
            stats = self.db.get_statistics(role, str(st.session_state.user['_id']))
            st.write(f"**Total Cases:** {stats['total_cases']}")
            st.write(f"**Open:** {stats['open_cases']}")
            st.write(f"**Critical:** {stats['critical_cases']}")
        
        # Logout button
        if st.sidebar.button("🚪 Logout", type="secondary", use_container_width=True):
            self.db.log_activity(
                user_id=str(st.session_state.user['_id']),
                username=st.session_state.user['username'],
                action="logout",
                details="User logged out"
            )
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.sidebar.markdown("---")
        st.sidebar.caption(f"© 2025 {Config.POLICE_STATION}")
        st.sidebar.caption("Version 2.0 - EPICS Project")
        
        return choice
    
    def dashboard(self):
        """Enhanced dashboard with comprehensive metrics"""
        user = st.session_state.user
        role = user.get('role')
        
        st.title(f"📊 {'My ' if role == Config.ROLE_CONSTABLE else ''}Dashboard")
        st.caption(f"Welcome back, {user['full_name']} | {datetime.now().strftime('%d %B %Y, %I:%M %p')}")
        
        # Get statistics
        stats = self.db.get_statistics(role, str(user['_id']))
        grievances = self.db.get_all_grievances(role, str(user['_id']))
        
        if not grievances:
            st.info("📭 No cases available. Start by creating a manual entry or importing CSV data.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✍️ Create Manual Entry", use_container_width=True):
                    st.session_state.nav_override = "✍️ Manual Entry"
                    st.rerun()
            with col2:
                if st.button("📁 Import CSV Data", use_container_width=True):
                    st.session_state.nav_override = "📁 CSV Import"
                    st.rerun()
            return
        
        # Key Metrics Row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("📋 Total Cases", stats['total_cases'])
        with col2:
            st.metric("🔓 Open", stats['open_cases'], 
                     delta=None if stats['total_cases'] == 0 else f"{(stats['open_cases']/stats['total_cases']*100):.0f}%")
        with col3:
            st.metric("⏳ In Progress", stats['in_progress'])
        with col4:
            st.metric("✅ Resolved", stats['resolved_cases'])
        with col5:
            st.metric("🔴 Critical", stats['critical_cases'])
        
        st.markdown("---")
        
        # Secondary Metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📈 Resolution Rate", f"{stats['resolution_rate']:.1f}%")
        with col2:
            st.metric("🔒 Closed Cases", stats['closed_cases'])
        with col3:
            # Calculate pending (Open + In Progress)
            pending = stats['open_cases'] + stats['in_progress']
            st.metric("⏰ Pending", pending)
        
        st.markdown("---")
        
        # Charts Row
        df = pd.DataFrame(grievances)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Status Distribution")
            status_counts = df['status'].value_counts()
            fig_status = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                color=status_counts.index,
                color_discrete_map=Config.STATUS_COLORS,
                hole=0.4
            )
            fig_status.update_traces(textposition='inside', textinfo='percent+label')
            fig_status.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            st.subheader("⚠️ Priority Breakdown")
            priority_counts = df['priority'].value_counts()
            fig_priority = px.bar(
                x=priority_counts.index,
                y=priority_counts.values,
                color=priority_counts.index,
                color_discrete_map=Config.PRIORITY_COLORS,
                labels={'x': 'Priority', 'y': 'Count'}
            )
            fig_priority.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig_priority, use_container_width=True)
        
        st.markdown("---")
        
        # Recent Cases Table
        st.subheader("🕒 Recent Cases (Last 10)")
        
        recent_grievances = grievances[:10]
        recent_data = []
        
        for g in recent_grievances:
            recent_data.append({
                'Case Number': g.get('case_number', 'N/A'),
                'Title': g.get('title', 'No Title')[:50] + ('...' if len(g.get('title', '')) > 50 else ''),
                'Category': g.get('category', 'Other'),
                'Status': g.get('status', 'Open'),
                'Priority': g.get('priority', 'Medium'),
                'Date': g.get('created_at', datetime.now()).strftime('%d-%m-%Y') if isinstance(g.get('created_at'), datetime) else str(g.get('created_at', 'N/A'))[:10]
            })
        
        st.dataframe(
            pd.DataFrame(recent_data),
            use_container_width=True,
            hide_index=True
        )
    
    def manual_entry(self):
        """Enhanced manual entry form with better validation"""
        st.title("✍️ Manual Case Entry")
        st.caption("Enter case details manually into the system")
        
        user = st.session_state.user
        
        with st.form("manual_entry_form", clear_on_submit=True):
            st.subheader("📋 Case Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input(
                    "📝 Case Title*",
                    placeholder="Brief description of the complaint",
                    help="Enter a concise title (max 100 characters)"
                )
                
                description = st.text_area(
                    "📄 Detailed Description*",
                    height=150,
                    placeholder="Provide complete details including time, location, witnesses, and sequence of events...",
                    help="Be as detailed as possible"
                )
                
                auto_categorize = st.checkbox("🤖 Auto-categorize based on description", value=True)
                
                if not auto_categorize:
                    category = st.selectbox("📂 Category*", Config.CATEGORIES)
                
                priority = st.selectbox(
                    "⚠️ Priority Level*",
                    Config.PRIORITY_LEVELS,
                    help="System will suggest priority based on content"
                )
            
            with col2:
                st.markdown("**Complainant Details:**")
                
                complainant_name = st.text_input(
                    "👤 Complainant Name*",
                    placeholder="Full name as per ID proof"
                )
                
                complainant_phone = st.text_input(
                    "📞 Contact Number*",
                    placeholder="10-digit mobile number",
                    max_chars=10
                )
                
                complainant_email = st.text_input(
                    "📧 Email (Optional)",
                    placeholder="email@example.com"
                )
                
                complainant_age = st.number_input(
                    "🎂 Age",
                    min_value=1,
                    max_value=120,
                    value=30
                )
            
            st.markdown("---")
            st.subheader("📍 Location & Time Details")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                district = st.selectbox(
                    "🏙️ District*",
                    list(self.geocoder.get_ap_districts_coordinates().keys())
                )
                
                area = st.text_input(
                    "🏘️ Area/Locality*",
                    placeholder="e.g., Benz Circle, MVP Colony"
                )
            
            with col2:
                location = st.text_area(
                    "📍 Full Address*",
                    height=100,
                    placeholder="House/Shop number, street name, landmarks..."
                )
            
            with col3:
                date_of_incident = st.date_input(
                    "📅 Date of Incident*",
                    value=datetime.now().date(),
                    max_value=datetime.now().date()
                )
                
                time_of_incident = st.time_input(
                    "🕐 Time of Incident (Approx)",
                    value=None
                )
                
                status = st.selectbox(
                    "📊 Initial Status*",
                    ["Open", "In Progress"]
                )
            
            st.markdown("---")
            
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.caption("* Required fields")
            
            with col2:
                submitted = st.form_submit_button(
                    "✅ Submit Case",
                    type="primary",
                    use_container_width=True
                )
            
            with col3:
                cancelled = st.form_submit_button(
                    "❌ Cancel",
                    use_container_width=True
                )
            
            if submitted:
                # Validation
                errors = []
                
                if not title or len(title.strip()) < 10:
                    errors.append("Title must be at least 10 characters")
                if not description or len(description.strip()) < 20:
                    errors.append("Description must be at least 20 characters")
                if not complainant_name:
                    errors.append("Complainant name is required")
                if not complainant_phone or len(complainant_phone) != 10:
                    errors.append("Valid 10-digit phone number is required")
                if not location or len(location.strip()) < 10:
                    errors.append("Full address is required")
                if not area:
                    errors.append("Area/Locality is required")
                
                if errors:
                    for error in errors:
                        st.error(f"❌ {error}")
                else:
                    # Process submission
                    if auto_categorize:
                        category = self.text_processor.categorize_grievance(f"{title} {description}")
                        suggested_priority = self.text_processor.extract_priority_indicators(description, category)
                        
                        if suggested_priority != priority:
                            st.warning(f"💡 Suggested priority based on content: **{suggested_priority}**")
                    
                    full_address = f"{location}, {area}, {district}, Andhra Pradesh"
                    
                    # Get coordinates
                    coords = self.geocoder.geocode_location(full_address)
                    
                    grievance_data = {
                        'title': title.strip(),
                        'description': description.strip(),
                        'category': category,
                        'priority': priority,
                        'status': status,
                        'complainant_name': complainant_name.strip(),
                        'complainant_phone': complainant_phone,
                        'complainant_email': complainant_email.strip() if complainant_email else '',
                        'complainant_age': complainant_age,
                        'location': full_address,
                        'district': district,
                        'area': area.strip(),
                        'date_of_incident': date_of_incident.strftime('%Y-%m-%d'),
                        'time_of_incident': time_of_incident.strftime('%H:%M:%S') if time_of_incident else 'Not specified',
                        'submitted_by': user['username'],
                        'submitted_by_id': str(user['_id']),
                        'submitted_by_name': user['full_name'],
                        'badge_number': user['badge_number'],
                        'station': user['station']
                    }
                    
                    if coords:
                        grievance_data['latitude'] = coords[0]
                        grievance_data['longitude'] = coords[1]
                    
                    try:
                        result = self.db.insert_grievance(grievance_data)
                        st.success(f"✅ Case submitted successfully!")
                        st.info(f"📋 **Case Number:** {grievance_data['case_number']}")
                        st.balloons()
                        
                        # Show case summary
                        with st.expander("📄 View Case Summary"):
                            st.json({
                                'Case Number': grievance_data['case_number'],
                                'Title': grievance_data['title'],
                                'Category': grievance_data['category'],
                                'Priority': grievance_data['priority'],
                                'Location': grievance_data['location'],
                                'Complainant': grievance_data['complainant_name']
                            })
                        
                    except Exception as e:
                        st.error(f"❌ Error submitting case: {str(e)}")
            
            if cancelled:
                st.info("Form cancelled")
    
    def csv_import(self):
        """Enhanced CSV import with better progress tracking"""
        st.title("📁 Bulk Import Cases from CSV")
        st.caption("Import multiple cases at once using a CSV file")
        
        user = st.session_state.user
        
        # Instructions
        with st.expander("📋 CSV Format Instructions & Requirements"):
            st.markdown("""
            ### Required Columns:
            - **title**: Brief case description (10-100 characters)
            - **description**: Detailed complaint (minimum 20 characters)
            
            ### Optional Columns:
            - category, priority, status
            - complainant_name, complainant_phone, complainant_email, complainant_age
            - location, district, area, latitude, longitude
            - date_of_incident, time_of_incident
            
            ### Example CSV Structure:
            ```
            title,description,category,priority,status,complainant_name,complainant_phone,location,district
            "Theft case","Mobile phone stolen...",Theft,High,Open,John Doe,9876543210,"MG Road",Vijayawada
            ```
            
            ### Tips:
            - Use UTF-8 encoding for best compatibility
            - Enclose text with commas in quotes
            - Maximum file size: 50MB
            - Recommended: 100-5000 rows per file
            """)
        
        # File uploader
        uploaded_file = st.file_uploader(
            "📂 Choose CSV file",
            type=['csv'],
            help="Select a CSV file with complaint data"
        )
        
        if uploaded_file is not None:
            # Display file info
            file_size = uploaded_file.size / 1024  # KB
            st.success(f"✅ File uploaded: **{uploaded_file.name}** ({file_size:.1f} KB)")
            
            # Process CSV
            with st.spinner("🔄 Processing CSV file..."):
                df, error = self.csv_processor.process_csv_file(uploaded_file)
            
            if error:
                st.error(f"❌ Error processing CSV: {error}")
                return
            
            # Validate structure
            is_valid, validation_message = self.csv_processor.validate_csv_structure(df)
            
            if not is_valid:
                st.error(f"❌ Validation Error: {validation_message}")
                return
            
            st.success(f"✅ {validation_message}")
            st.info(f"📊 Found **{len(df)}** rows in CSV file")
            
            # Show preview
            with st.expander("👁️ Preview Data (First 10 Rows)"):
                st.dataframe(df.head(10), use_container_width=True)
            
            # Show column information
            with st.expander("ℹ️ Column Information"):
                col_info = pd.DataFrame({
                    'Column': df.columns,
                    'Type': df.dtypes.astype(str),
                    'Non-Null Count': df.count(),
                    'Sample Value': df.iloc[0] if len(df) > 0 else ''
                })
                st.dataframe(col_info, use_container_width=True)
            
            st.markdown("---")
            st.subheader("⚙️ Import Configuration")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                auto_categorize = st.checkbox(
                    "🤖 Auto-categorize cases",
                    value=True,
                    help="Automatically determine category based on description"
                )
                
                skip_duplicates = st.checkbox(
                    "🔄 Skip duplicate titles",
                    value=True,
                    help="Avoid importing cases with same title"
                )
            
            with col2:
                default_status = st.selectbox(
                    "📊 Default Status",
                    Config.STATUS_OPTIONS,
                    help="Status for cases without status column"
                )
                
                default_priority = st.selectbox(
                    "⚠️ Default Priority",
                    Config.PRIORITY_LEVELS,
                    index=1,
                    help="Priority for cases without priority column"
                )
            
            with col3:
                validate_phone = st.checkbox(
                    "📞 Validate phone numbers",
                    value=True,
                    help="Check if phone numbers are valid"
                )
                
                geocode_locations = st.checkbox(
                    "🗺️ Geocode addresses",
                    value=False,
                    help="Convert addresses to coordinates (slower but enables mapping)"
                )
            
            st.markdown("---")
            
            # Import button
            if st.button("📥 Start Import Process", type="primary", use_container_width=True):
                imported_count = 0
                skipped_count = 0
                error_count = 0
                errors = []
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                stats_placeholder = st.empty()
                
                start_time = datetime.now()
                
                for index, row in df.iterrows():
                    try:
                        title = str(row.get('title', '')).strip()
                        description = str(row.get('description', '')).strip()
                        
                        # Skip if missing required fields
                        if not title or not description:
                            skipped_count += 1
                            continue
                        
                        # Check duplicates
                        if skip_duplicates:
                            existing = self.db.grievances.find_one({"title": title})
                            if existing:
                                skipped_count += 1
                                continue
                        
                        # Validate phone if enabled
                        phone = str(row.get('complainant_phone', ''))
                        if validate_phone and phone and len(phone) != 10:
                            skipped_count += 1
                            errors.append(f"Row {index + 1}: Invalid phone number")
                            continue
                        
                        # Prepare data
                        category = row.get('category', 'Other')
                        if auto_categorize and category == 'Other':
                            category = self.text_processor.categorize_grievance(f"{title} {description}")
                        
                        grievance_data = {
                            'title': title,
                            'description': description,
                            'category': category,
                            'priority': row.get('priority', default_priority),
                            'status': row.get('status', default_status),
                            'complainant_name': str(row.get('complainant_name', 'Bulk Import')).strip(),
                            'complainant_phone': phone,
                            'complainant_email': str(row.get('complainant_email', '')).strip(),
                            'complainant_age': int(row.get('complainant_age', 30)) if pd.notna(row.get('complainant_age')) else 30,
                            'location': str(row.get('location', 'Not specified')).strip(),
                            'district': str(row.get('district', 'Not specified')).strip(),
                            'area': str(row.get('area', 'Not specified')).strip(),
                            'date_of_incident': str(row.get('date_of_incident', datetime.now().date())),
                            'time_of_incident': str(row.get('time_of_incident', 'Not specified')),
                            'submitted_by': user['username'],
                            'submitted_by_id': str(user['_id']),
                            'submitted_by_name': user['full_name'],
                            'badge_number': user['badge_number'],
                            'station': user['station']
                        }
                        
                        # Geocode if enabled (slower)
                        if geocode_locations:
                            coords = self.geocoder.geocode_location(grievance_data['location'])
                            if coords:
                                grievance_data['latitude'] = coords[0]
                                grievance_data['longitude'] = coords[1]
                        elif 'latitude' in row and 'longitude' in row:
                            if pd.notna(row['latitude']) and pd.notna(row['longitude']):
                                grievance_data['latitude'] = float(row['latitude'])
                                grievance_data['longitude'] = float(row['longitude'])
                        
                        # Insert to database
                        self.db.insert_grievance(grievance_data)
                        imported_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Row {index + 1}: {str(e)[:50]}")
                    
                    # Update progress
                    progress = (index + 1) / len(df)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing row {index + 1} of {len(df)}...")
                    
                    # Update stats
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    rate = (index + 1) / elapsed_time if elapsed_time > 0 else 0
                    eta = (len(df) - (index + 1)) / rate if rate > 0 else 0
                    
                    stats_placeholder.info(
                        f"✅ Imported: {imported_count} | "
                        f"⏭️ Skipped: {skipped_count} | "
                        f"❌ Errors: {error_count} | "
                        f"⏱️ ETA: {eta:.0f}s"
                    )
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                stats_placeholder.empty()
                
                # Show final results
                st.markdown("---")
                st.success(f"🎉 Import completed in {(datetime.now() - start_time).total_seconds():.1f} seconds!")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("✅ Successfully Imported", imported_count)
                with col2:
                    st.metric("⏭️ Skipped", skipped_count)
                with col3:
                    st.metric("❌ Errors", error_count)
                
                # Show errors if any
                if errors:
                    with st.expander(f"⚠️ View Errors ({len(errors)})"):
                        for error in errors[:50]:  # Show first 50 errors
                            st.text(f"• {error}")
                        if len(errors) > 50:
                            st.caption(f"... and {len(errors) - 50} more errors")
                
                st.balloons()
    
    def view_cases(self):
        """Enhanced case viewing with advanced filtering"""
        user = st.session_state.user
        role = user.get('role')
        
        st.title("📋 View All Cases" if role != Config.ROLE_CONSTABLE else "📋 My Cases")
        
        # Advanced Filters
        with st.expander("🔍 Advanced Filters", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                status_filter = st.selectbox("📊 Status", ["All"] + Config.STATUS_OPTIONS)
            
            with col2:
                category_filter = st.selectbox("📂 Category", ["All"] + Config.CATEGORIES)
            
            with col3:
                priority_filter = st.selectbox("⚠️ Priority", ["All"] + Config.PRIORITY_LEVELS)
            
            with col4:
                district_filter = st.selectbox("🏙️ District", ["All"] + list(self.geocoder.get_ap_districts_coordinates().keys()))
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                date_from = st.date_input("📅 From Date", value=None)
            
            with col2:
                date_to = st.date_input("📅 To Date", value=None)
            
            with col3:
                search_query = st.text_input("🔍 Search", placeholder="Case number, title, or description...")
        
        # Build filters
        filters = {}
        if status_filter != "All":
            filters['status'] = status_filter
        if category_filter != "All":
            filters['category'] = category_filter
        if priority_filter != "All":
            filters['priority'] = priority_filter
        if district_filter != "All":
            filters['district'] = district_filter
        if date_from:
            filters['date_from'] = datetime.combine(date_from, datetime.min.time())
        if date_to:
            filters['date_to'] = datetime.combine(date_to, datetime.max.time())
        
        # Get filtered grievances
        grievances = self.db.get_all_grievances(role, str(user['_id']), filters)
        
        # Apply text search
        if search_query:
            search_lower = search_query.lower()
            grievances = [
                g for g in grievances
                if search_lower in g.get('case_number', '').lower()
                or search_lower in g.get('title', '').lower()
                or search_lower in g.get('description', '').lower()
            ]
        
        st.markdown("---")
        
        # Results summary
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"📊 Found **{len(grievances)}** cases matching filters")
        
        with col2:
            sort_by = st.selectbox("Sort by:", ["Date (Newest)", "Date (Oldest)", "Priority", "Status"])
        
        with col3:
            view_mode = st.radio("View:", ["List", "Table"], horizontal=True, label_visibility="collapsed")
        
        if not grievances:
            st.info("No cases match the selected filters.")
            return
        
        # Sort grievances
        if sort_by == "Date (Oldest)":
            grievances.sort(key=lambda x: x.get('created_at', datetime.now()))
        elif sort_by == "Priority":
            priority_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
            grievances.sort(key=lambda x: priority_order.get(x.get('priority', 'Medium'), 2))
        elif sort_by == "Status":
            grievances.sort(key=lambda x: x.get('status', 'Open'))
        
        # Display cases
        if view_mode == "Table":
            # Table view
            table_data = []
            for g in grievances:
                table_data.append({
                    'Case Number': g.get('case_number', 'N/A'),
                    'Title': g.get('title', 'No Title')[:60] + ('...' if len(g.get('title', '')) > 60 else ''),
                    'Category': g.get('category', 'Other'),
                    'Status': g.get('status', 'Open'),
                    'Priority': g.get('priority', 'Medium'),
                    'District': g.get('district', 'N/A'),
                    'Date': g.get('created_at', datetime.now()).strftime('%d-%m-%Y') if isinstance(g.get('created_at'), datetime) else str(g.get('created_at', 'N/A'))[:10]
                })
            
            st.dataframe(
                pd.DataFrame(table_data),
                use_container_width=True,
                hide_index=True
            )
        
        else:
            # List view (expandable cards)
            for i, grievance in enumerate(grievances):
                case_id = str(grievance['_id'])
                case_number = grievance.get('case_number', 'N/A')
                priority = grievance.get('priority', 'Medium')
                status = grievance.get('status', 'Open')
                
                # Priority indicator
                indicators = {'Critical': '🔴', 'High': '🟠', 'Medium': '🟡', 'Low': '🟢'}
                indicator = indicators.get(priority, '🟡')
                
                with st.expander(f"{indicator} **{case_number}** - {grievance.get('title', 'No Title')[:50]} [{status}]"):
                    # Case details
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**Basic Information:**")
                        st.write(f"**Category:** {grievance.get('category', 'General')}")
                        st.write(f"**Priority:** {priority}")
                        st.write(f"**Status:** {status}")
                    
                    with col2:
                        st.markdown("**Location:**")
                        st.write(f"**District:** {grievance.get('district', 'N/A')}")
                        st.write(f"**Area:** {grievance.get('area', 'N/A')}")
                        st.write(f"**Address:** {grievance.get('location', 'N/A')[:50]}")
                    
                    with col3:
                        st.markdown("**Complainant:**")
                        st.write(f"**Name:** {grievance.get('complainant_name', 'Unknown')}")
                        st.write(f"**Phone:** {grievance.get('complainant_phone', 'N/A')}")
                        st.write(f"**Email:** {grievance.get('complainant_email', 'N/A') or 'Not provided'}")
                    
                    st.markdown("---")
                    st.markdown("**Description:**")
                    st.write(grievance.get('description', 'No description'))
                    
                    st.markdown("---")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.caption(f"**Created:** {grievance.get('created_at', 'Unknown')}")
                        st.caption(f"**Incident Date:** {grievance.get('date_of_incident', 'N/A')}")
                    
                    with col2:
                        st.caption(f"**Submitted by:** {grievance.get('submitted_by_name', 'Unknown')}")
                        st.caption(f"**Badge:** {grievance.get('badge_number', 'N/A')}")
                    
                    with col3:
                        st.caption(f"**Last Updated:** {grievance.get('updated_at', 'N/A')}")
                    
                    # Actions (only for officers and admins)
                    if role in [Config.ROLE_OFFICER, Config.ROLE_ADMIN]:
                        st.markdown("---")
                        st.markdown("**Actions:**")
                        
                        action_col1, action_col2, action_col3 = st.columns(3)
                        
                        with action_col1:
                            new_status = st.selectbox(
                                "Update Status",
                                Config.STATUS_OPTIONS,
                                key=f"status_{case_id}",
                                index=Config.STATUS_OPTIONS.index(status)
                            )
                        
                        with action_col2:
                            remarks = st.text_input("Remarks", key=f"remarks_{case_id}", placeholder="Optional")
                        
                        with action_col3:
                            st.write("")  # Spacing
                            st.write("")  # Spacing
                            if st.button("💾 Update", key=f"save_{case_id}"):
                                self.db.update_grievance(
                                    case_id,
                                    {"status": new_status, "remarks": remarks},
                                    str(user['_id']),
                                    user['username']
                                )
                                st.success("✅ Status updated!")
                                st.rerun()
    
    def show_analytics(self):
        """Enhanced analytics with multiple visualization options"""
        st.title("📈 Advanced Analytics Dashboard")
        
        user = st.session_state.user
        role = user.get('role')
        
        grievances = self.db.get_all_grievances(role, str(user['_id']))
        
        if not grievances:
            st.warning("📭 No data available for analysis. Import cases to see analytics.")
            return
        
        df = pd.DataFrame(grievances)
        
        # Key Metrics Row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("📋 Total Cases", len(df))
        with col2:
            open_rate = (len(df[df['status'] == 'Open']) / len(df) * 100) if len(df) > 0 else 0
            st.metric("🔓 Open Rate", f"{open_rate:.1f}%")
        with col3:
            resolution_rate = (len(df[df['status'] == 'Resolved']) / len(df) * 100) if len(df) > 0 else 0
            st.metric("✅ Resolution Rate", f"{resolution_rate:.1f}%")
        with col4:
            critical_count = len(df[df['priority'] == 'Critical'])
            st.metric("🔴 Critical Cases", critical_count)
        with col5:
            pending = len(df[df['status'].isin(['Open', 'In Progress'])])
            st.metric("⏰ Pending", pending)
        
        st.markdown("---")
        
        # Main Charts
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Trends", "🗺️ Geographic", "📋 Detailed"])
        
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Status Distribution")
                status_counts = df['status'].value_counts()
                fig_status = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    color=status_counts.index,
                    color_discrete_map=Config.STATUS_COLORS,
                    hole=0.4
                )
                fig_status.update_traces(textposition='inside', textinfo='percent+label+value')
                fig_status.update_layout(height=400)
                st.plotly_chart(fig_status, use_container_width=True)
            
            with col2:
                st.subheader("Priority Distribution")
                priority_counts = df['priority'].value_counts()
                fig_priority = px.bar(
                    x=priority_counts.index,
                    y=priority_counts.values,
                    color=priority_counts.index,
                    color_discrete_map=Config.PRIORITY_COLORS,
                    labels={'x': 'Priority', 'y': 'Number of Cases'}
                )
                fig_priority.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig_priority, use_container_width=True)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Top 10 Categories")
                category_counts = df['category'].value_counts().head(10)
                fig_category = px.bar(
                    x=category_counts.values,
                    y=category_counts.index,
                    orientation='h',
                    labels={'x': 'Count', 'y': 'Category'},
                    color=category_counts.values,
                    color_continuous_scale='Viridis'
                )
                fig_category.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
                st.plotly_chart(fig_category, use_container_width=True)
            
            with col2:
                st.subheader("Category-wise Status")
                category_status = pd.crosstab(df['category'], df['status'])
                fig_stacked = px.bar(
                    category_status.head(10),
                    barmode='stack',
                    labels={'value': 'Count', 'variable': 'Status'},
                    color_discrete_map=Config.STATUS_COLORS
                )
                fig_stacked.update_layout(height=400, yaxis_title="Count", xaxis_title="Category")
                st.plotly_chart(fig_stacked, use_container_width=True)
        
        with tab2:
            st.subheader("Time-based Analysis")
            
            # Convert dates
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['date'] = df['created_at'].dt.date
            df['month'] = df['created_at'].dt.to_period('M')
            df['hour'] = df['created_at'].dt.hour
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Monthly Trend**")
                monthly_counts = df.groupby('month').size()
                fig_monthly = px.line(
                    x=monthly_counts.index.astype(str),
                    y=monthly_counts.values,
                    labels={'x': 'Month', 'y': 'Number of Cases'},
                    markers=True
                )
                fig_monthly.update_layout(height=300)
                st.plotly_chart(fig_monthly, use_container_width=True)
            
            with col2:
                st.markdown("**Daily Registration Pattern**")
                daily_counts = df.groupby('date').size().tail(30)
                fig_daily = px.bar(
                    x=daily_counts.index,
                    y=daily_counts.values,
                    labels={'x': 'Date', 'y': 'Cases Registered'}
                )
                fig_daily.update_layout(height=300)
                st.plotly_chart(fig_daily, use_container_width=True)
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Hourly Distribution**")
                hourly_counts = df.groupby('hour').size()
                fig_hourly = px.bar(
                    x=hourly_counts.index,
                    y=hourly_counts.values,
                    labels={'x': 'Hour of Day', 'y': 'Number of Cases'}
                )
                fig_hourly.update_layout(height=300)
                st.plotly_chart(fig_hourly, use_container_width=True)
            
            with col2:
                st.markdown("**Category Trend (Top 5)**")
                top_categories = df['category'].value_counts().head(5).index
                df_top = df[df['category'].isin(top_categories)]
                category_monthly = df_top.groupby(['month', 'category']).size().reset_index(name='count')
                category_monthly['month'] = category_monthly['month'].astype(str)
                
                fig_cat_trend = px.line(
                    category_monthly,
                    x='month',
                    y='count',
                    color='category',
                    labels={'month': 'Month', 'count': 'Cases'}
                )
                fig_cat_trend.update_layout(height=300)
                st.plotly_chart(fig_cat_trend, use_container_width=True)
        
        with tab3:
            st.subheader("Geographic Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Cases by District**")
                if 'district' in df.columns:
                    district_counts = df['district'].value_counts().head(10)
                    fig_district = px.bar(
                        x=district_counts.values,
                        y=district_counts.index,
                        orientation='h',
                        labels={'x': 'Number of Cases', 'y': 'District'},
                        color=district_counts.values,
                        color_continuous_scale='Blues'
                    )
                    fig_district.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
                    st.plotly_chart(fig_district, use_container_width=True)
                else:
                    st.info("District information not available")
            
            with col2:
                st.markdown("**Priority by District (Top 5)**")
                if 'district' in df.columns:
                    top_districts = df['district'].value_counts().head(5).index
                    df_top_districts = df[df['district'].isin(top_districts)]
                    district_priority = pd.crosstab(df_top_districts['district'], df_top_districts['priority'])
                    
                    fig_dist_priority = px.bar(
                        district_priority,
                        barmode='group',
                        labels={'value': 'Count', 'variable': 'Priority'},
                        color_discrete_map=Config.PRIORITY_COLORS
                    )
                    fig_dist_priority.update_layout(height=400)
                    st.plotly_chart(fig_dist_priority, use_container_width=True)
                else:
                    st.info("District information not available")
        
        with tab4:
            st.subheader("Detailed Statistics")
            
            # Category Statistics
            st.markdown("**Category-wise Detailed Stats**")
            category_stats = df.groupby('category').agg({
                'case_number': 'count',
                'status': lambda x: (x == 'Resolved').sum(),
                'priority': lambda x: (x == 'Critical').sum()
            }).rename(columns={
                'case_number': 'Total',
                'status': 'Resolved',
                'priority': 'Critical'
            })
            category_stats['Resolution Rate'] = (category_stats['Resolved'] / category_stats['Total'] * 100).round(1)
            category_stats = category_stats.sort_values('Total', ascending=False)
            
            st.dataframe(category_stats, use_container_width=True)
            
            st.markdown("---")
            
            # Status transition
            st.markdown("**Status Summary**")
            status_summary = df.groupby('status').agg({
                'case_number': 'count',
                'priority': lambda x: (x == 'Critical').sum()
            }).rename(columns={'case_number': 'Total Cases', 'priority': 'Critical Priority'})
            
            st.dataframe(status_summary, use_container_width=True)
    
    def show_location_map(self):
        """Interactive location map with clustering"""
        st.title("🗺️ Grievance Location Map")
        st.caption("Interactive map showing geographic distribution of complaints")
        
        user = st.session_state.user
        role = user.get('role')
        
        grievances = self.db.get_all_grievances(role, str(user['_id']))
        
        if not grievances:
            st.warning("📭 No grievances available to map.")
            return
        
        # Filters
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status_filter = st.selectbox("Status", ["All"] + Config.STATUS_OPTIONS, key="map_status")
        with col2:
            priority_filter = st.selectbox("Priority", ["All"] + Config.PRIORITY_LEVELS, key="map_priority")
        with col3:
            category_filter = st.selectbox("Category", ["All"] + Config.CATEGORIES[:10], key="map_category")
        with col4:
            map_type = st.selectbox("Map Type", ["Standard", "Satellite", "Terrain"])
        
        # Apply filters
        filtered_grievances = grievances
        if status_filter != "All":
            filtered_grievances = [g for g in filtered_grievances if g.get('status') == status_filter]
        if priority_filter != "All":
            filtered_grievances = [g for g in filtered_grievances if g.get('priority') == priority_filter]
        if category_filter != "All":
            filtered_grievances = [g for g in filtered_grievances if g.get('category') == category_filter]
        
        st.write(f"📍 Showing **{len(filtered_grievances)}** cases on map")
        
        # Create map
        tile_map = {
            "Standard": "OpenStreetMap",
            "Satellite": "Esri WorldImagery",
            "Terrain": "Stamen Terrain"
        }
        
        m = folium.Map(
            location=self.geocoder.ap_center,
            zoom_start=7,
            tiles=tile_map.get(map_type, "OpenStreetMap")
        )
        
        # Color mapping
        priority_colors = {
            'Critical': 'red',
            'High': 'orange',
            'Medium': 'blue',
            'Low': 'green'
        }
        
        # Use marker clustering for better performance
        marker_cluster = MarkerCluster().add_to(m)
        
        total_cases = len(filtered_grievances)
        mapped_cases = 0
        unmapped_cases = []
        
        with st.spinner("🗺️ Geocoding locations and creating map..."):
            progress_bar = st.progress(0)
            
            for idx, grievance in enumerate(filtered_grievances):
                location_string = grievance.get('location', '')
                
                # Try to get coordinates
                coords = None
                
                # First: Check if already geocoded
                if 'latitude' in grievance and 'longitude' in grievance:
                    lat = grievance.get('latitude')
                    lon = grievance.get('longitude')
                    if lat and lon:
                        coords = (float(lat), float(lon))
                
                # Second: Match with known districts
                if not coords:
                    districts = self.geocoder.get_ap_districts_coordinates()
                    for district, district_coords in districts.items():
                        if district.lower() in location_string.lower():
                            coords = district_coords
                            break

                # Third: Geocode the address (rate-limited)
                if not coords and idx % 10 == 0:  # Geocode every 10th to avoid rate limits
                    coords = self.geocoder.geocode_location(location_string)
                
                if coords:
                    priority = grievance.get('priority', 'Medium')
                    
                    # Create popup
                    popup_html = f"""
                    <div style="width: 250px; font-family: Arial;">
                        <h4 style="margin-bottom: 8px; color: #2c3e50;">{grievance.get('case_number', 'N/A')}</h4>
                        <p style="margin: 4px 0;"><b>Title:</b> {grievance.get('title', 'No title')[:50]}...</p>
                        <p style="margin: 4px 0;"><b>Category:</b> {grievance.get('category', 'N/A')}</p>
                        <p style="margin: 4px 0;"><b>Priority:</b> <span style="color: {priority_colors.get(priority, 'gray')};">{priority}</span></p>
                        <p style="margin: 4px 0;"><b>Status:</b> {grievance.get('status', 'Open')}</p>
                        <p style="margin: 4px 0;"><b>Location:</b> {grievance.get('area', 'N/A')}, {grievance.get('district', 'N/A')}</p>
                        <p style="margin: 4px 0; font-size: 11px; color: gray;"><b>Date:</b> {grievance.get('date_of_incident', 'N/A')}</p>
                    </div>
                    """
                    
                    # Add marker
                    folium.Marker(
                        location=coords,
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=f"{grievance.get('case_number', 'N/A')} - {priority}",
                        icon=folium.Icon(
                            color=priority_colors.get(priority, 'blue'),
                            icon='info-sign',
                            prefix='fa'
                        )
                    ).add_to(marker_cluster)
                    
                    mapped_cases += 1
                else:
                    unmapped_cases.append({
                        'case_number': grievance.get('case_number', 'N/A'),
                        'location': location_string
                    })
                
                progress_bar.progress((idx + 1) / total_cases)
            
            progress_bar.empty()
        
        # Display map
        st.markdown("---")
        st_folium(m, width=1200, height=600)
        
        # Statistics
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📍 Total Cases", total_cases)
        with col2:
            st.metric("✅ Mapped", mapped_cases)
        with col3:
            st.metric("❌ Unmapped", len(unmapped_cases))
        with col4:
            mapping_rate = (mapped_cases / total_cases * 100) if total_cases > 0 else 0
            st.metric("📊 Mapping Rate", f"{mapping_rate:.1f}%")
        
        # Unmapped cases
        if unmapped_cases:
            with st.expander(f"⚠️ View {len(unmapped_cases)} Unmapped Cases"):
                st.warning("These cases couldn't be geocoded. Consider adding more specific location details.")
                for case in unmapped_cases[:30]:
                    st.write(f"• **{case['case_number']}**: {case['location']}")
                if len(unmapped_cases) > 30:
                    st.caption(f"... and {len(unmapped_cases) - 30} more unmapped cases")
    
    def show_crime_heatmap(self):
        """Crime density heatmap"""
        st.title("🔥 Crime Density Heatmap")
        st.caption("Visualize crime concentration across different areas")
        
        user = st.session_state.user
        role = user.get('role')
        grievances = self.db.get_all_grievances(role, str(user['_id']))
        
        if not grievances:
            st.warning("📭 No data available for heatmap.")
            return
        
        # Category filter
        col1, col2 = st.columns(2)
        with col1:
            category_filter = st.multiselect(
                "Filter by Category",
                Config.CATEGORIES,
                default=[],
                help="Leave empty to show all categories"
            )
        with col2:
            intensity_by = st.selectbox(
                "Intensity Based On",
                ["Priority", "Count"],
                help="Priority: Critical cases show hotter | Count: More cases = hotter"
            )
        
        # Filter by category
        if category_filter:
            grievances = [g for g in grievances if g.get('category') in category_filter]
        
        st.write(f"🔥 Generating heatmap from **{len(grievances)}** cases")
        
        heat_data = []
        
        with st.spinner("🔥 Generating heatmap..."):
            for grievance in grievances:
                coords = None
                
                # Get coordinates
                if 'latitude' in grievance and 'longitude' in grievance:
                    lat = grievance.get('latitude')
                    lon = grievance.get('longitude')
                    if lat and lon:
                        coords = (float(lat), float(lon))
                
                if not coords:
                    location_string = grievance.get('location', '')
                    coords = self.geocoder.geocode_location(location_string)
                
                if coords:
                    if intensity_by == "Priority":
                        intensity = {
                            'Critical': 1.0,
                            'High': 0.7,
                            'Medium': 0.4,
                            'Low': 0.2
                        }.get(grievance.get('priority', 'Medium'), 0.5)
                    else:
                        intensity = 0.5  # Equal weight for count-based
                    
                    heat_data.append([coords[0], coords[1], intensity])
        
        if not heat_data:
            st.error("❌ No locations could be geocoded for heatmap.")
            st.info("💡 Tip: Ensure your cases have proper location information or latitude/longitude coordinates.")
            return
        
        # Create heatmap
        m = folium.Map(
            location=self.geocoder.ap_center,
            zoom_start=7,
            tiles='CartoDB positron'
        )
        
        HeatMap(
            heat_data,
            min_opacity=0.2,
            radius=20,
            blur=25,
            gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 0.8: 'orange', 1.0: 'red'}
        ).add_to(m)
        
        st_folium(m, width=1200, height=600)
        
        st.success(f"✅ Heatmap generated from {len(heat_data)} geocoded locations")
        
        # Legend
        st.markdown("---")
        st.subheader("🎨 Heatmap Legend")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Color Intensity:**")
            st.markdown("🔵 **Blue** - Low intensity/priority")
            st.markdown("🟢 **Green-Yellow** - Medium intensity")
            st.markdown("🟠 **Orange** - High intensity")
            st.markdown("🔴 **Red** - Critical/Highest intensity")
        
        with col2:
            st.markdown("**Interpretation:**")
            st.write("- Hotspots (red areas) indicate high concentration of cases")
            st.write("- Use this to identify crime-prone areas")
            st.write("- Helps in resource allocation and patrol planning")
    
    def case_assignment(self):
        """Case assignment workflow (Officer/Admin only)"""
        if st.session_state.user.get('role') not in [Config.ROLE_OFFICER, Config.ROLE_ADMIN]:
            st.error("❌ Access Denied. Officer or Admin privileges required.")
            return
        
        st.title("🎯 Case Assignment")
        st.caption("Assign cases to officers for investigation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Unassigned Cases")
            
            unassigned = list(self.db.grievances.find({
                "$or": [
                    {"assigned_to": {"$exists": False}},
                    {"assigned_to": None},
                    {"assigned_to": ""}
                ]
            }).limit(50))
            
            if not unassigned:
                st.info("✅ No unassigned cases available.")
                return
            
            st.write(f"Found **{len(unassigned)}** unassigned cases")
            
            case_options = {}
            for g in unassigned:
                label = f"{g['case_number']} - {g['title'][:50]} [{g['priority']}]"
                case_options[label] = str(g['_id'])
            
            selected_case = st.selectbox(
                "Select Case to Assign",
                options=list(case_options.keys()),
                help="Choose a case from unassigned cases"
            )
            
            if selected_case:
                case_id = case_options[selected_case]
                case_details = self.db.grievances.find_one({"_id": ObjectId(case_id)})
                
                with st.expander("📄 View Case Details"):
                    st.write(f"**Case Number:** {case_details['case_number']}")
                    st.write(f"**Category:** {case_details.get('category', 'N/A')}")
                    st.write(f"**Priority:** {case_details.get('priority', 'Medium')}")
                    st.write(f"**Location:** {case_details.get('location', 'N/A')}")
                    st.write(f"**Description:** {case_details.get('description', 'N/A')[:200]}...")
        
        with col2:
            st.subheader("👮 Assign To")
            
            # Get all constables and officers
            assignable_users = list(self.db.users.find({
                "role": {"$in": [Config.ROLE_CONSTABLE, Config.ROLE_OFFICER]},
                "is_active": True
            }))
            
            if not assignable_users:
                st.warning("⚠️ No officers or constables available for assignment.")
                return
            
            user_options = {}
            for u in assignable_users:
                label = f"{u['full_name']} ({u['badge_number']}) - {u['role'].replace('_', ' ').title()}"
                user_options[label] = u['username']
            
            selected_user = st.selectbox(
                "Select Officer/Constable",
                options=list(user_options.keys()),
                help="Choose who will handle this case"
            )
            
            assigned_to_username = user_options[selected_user]
            
            # Assignment notes
            assignment_notes = st.text_area(
                "Assignment Notes (Optional)",
                placeholder="Add any special instructions or notes for the assigned officer...",
                height=100
            )
            
            st.markdown("---")
            
            if st.button("✅ Assign Case", type="primary", use_container_width=True):
                user = st.session_state.user
                success, message = self.db.assign_case(
                    case_id,
                    assigned_to_username,
                    str(user['_id']),
                    user['username']
                )
                
                if success:
                    st.success(f"✅ {message}")
                    st.balloons()
                    
                    # Log with notes
                    if assignment_notes:
                        self.db.log_activity(
                            user_id=str(user['_id']),
                            username=user['username'],
                            action="case_assignment_notes",
                            details=f"Notes: {assignment_notes}"
                        )
                    
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    
    def user_management(self):
        """User management (Admin only)"""
        if st.session_state.user.get('role') != Config.ROLE_ADMIN:
            st.error("❌ Access Denied. Admin privileges required.")
            return
        
        st.title("👥 User Management")
        st.caption("Manage system users and their access")
        
        tab1, tab2 = st.tabs(["📋 All Users", "➕ Add New User"])
        
        with tab1:
            st.subheader("Registered Users")
            
            users = self.db.get_all_users()
            
            if not users:
                st.info("No users found.")
                return
            
            # Create user table
            user_data = []
            for user in users:
                user_data.append({
                    'Full Name': user['full_name'],
                    'Username': user['username'],
                    'Badge': user['badge_number'],
                    'Role': user['role'].replace('_', ' ').title(),
                    'Station': user['station'],
                    'Last Login': user.get('last_login', 'Never').strftime('%d-%m-%Y %H:%M') if user.get('last_login') else 'Never',
                    'Status': '✅ Active' if user.get('is_active', True) else '❌ Inactive'
                })
            
            st.dataframe(pd.DataFrame(user_data), use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("User Details")
            
            for user in users:
                with st.expander(f"👤 {user['full_name']} ({user['username']})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Role:** {user['role'].replace('_', ' ').title()}")
                        st.write(f"**Badge Number:** {user['badge_number']}")
                        st.write(f"**Station:** {user['station']}")
                    
                    with col2:
                        st.write(f"**Email:** {user.get('email', 'Not provided')}")
                        st.write(f"**Created:** {user['created_at'].strftime('%d-%m-%Y')}")
                        st.write(f"**Last Login:** {user.get('last_login', 'Never')}")
                    
                    # Show case statistics for constables
                    if user['role'] == Config.ROLE_CONSTABLE:
                        cases = self.db.grievances.count_documents({"submitted_by_id": str(user['_id'])})
                        resolved = self.db.grievances.count_documents({
                            "submitted_by_id": str(user['_id']),
                            "status": "Resolved"
                        })
                        st.info(f"📊 **Cases Submitted:** {cases} | **Resolved:** {resolved}")
        
        with tab2:
            st.subheader("Create New User")
            
            with st.form("new_user_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_username = st.text_input("Username*", placeholder="e.g., officer2")
                    new_password = st.text_input("Password*", type="password", placeholder="Minimum 6 characters")
                    confirm_password = st.text_input("Confirm Password*", type="password")
                    new_full_name = st.text_input("Full Name*", placeholder="Full name as per ID")
                
                with col2:
                    new_role = st.selectbox("Role*", [
                        Config.ROLE_CONSTABLE,
                        Config.ROLE_OFFICER,
                        Config.ROLE_ADMIN
                    ], format_func=lambda x: x.replace('_', ' ').title())
                    new_badge = st.text_input("Badge Number*", placeholder="e.g., PC003")
                    new_station = st.text_input("Police Station*", placeholder="e.g., Vijayawada Central")
                    new_email = st.text_input("Email (Optional)", placeholder="email@appolice.gov.in")
                
                st.caption("* Required fields")
                
                submitted = st.form_submit_button("➕ Create User", type="primary", use_container_width=True)
                
                if submitted:
                    errors = []
                    
                    if not all([new_username, new_password, new_full_name, new_badge, new_station]):
                        errors.append("All required fields must be filled")
                    if new_password != confirm_password:
                        errors.append("Passwords do not match")
                    if len(new_password) < 6:
                        errors.append("Password must be at least 6 characters")
                    
                    if errors:
                        for error in errors:
                            st.error(f"❌ {error}")
                    else:
                        success, message = self.db.create_user(
                            new_username, new_password, new_role,
                            new_full_name, new_badge, new_station, new_email
                        )
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.balloons()
                            st.info(f"**Login Credentials:** Username: `{new_username}` | Password: `{new_password}`")
                        else:
                            st.error(f"❌ {message}")
    
    def activity_logs(self):
        """Activity logs viewer (Admin only)"""
        if st.session_state.user.get('role') != Config.ROLE_ADMIN:
            st.error("❌ Access Denied. Admin privileges required.")
            return
        
        st.title("📜 System Activity Logs")
        st.caption("View system activity and audit trail")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            log_limit = st.selectbox("Show last:", [50, 100, 200, 500], index=1)
        
        with col2:
            action_filter = st.selectbox("Filter by Action", [
                "All", "login", "logout", "create_grievance", "update_grievance",
                "assign_case", "create_user"
            ])
        
        with col3:
            user_filter = st.text_input("Filter by Username", placeholder="Leave empty for all users")
        
        # Build filters
        filters = {}
        if action_filter != "All":
            filters['action'] = action_filter
        if user_filter:
            filters['username'] = user_filter
        
        logs = self.db.get_activity_logs(limit=log_limit, filters=filters)
        
        if not logs:
            st.info("No activity logs found matching the filters.")
            return
        
        st.write(f"📊 Showing **{len(logs)}** activity logs")
        
        # Display logs
        for log in logs:
            timestamp = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            
            # Color code by action
            if log['action'] == 'login':
                icon = "🔓"
            elif log['action'] == 'logout':
                icon = "🔒"
            elif log['action'] in ['create_grievance', 'update_grievance']:
                icon = "📝"
            elif log['action'] == 'assign_case':
                icon = "🎯"
            else:
                icon = "ℹ️"
            
            with st.expander(f"{icon} {timestamp} - **{log['action']}** by {log['username']}"):
                st.write(f"**User ID:** {log['user_id']}")
                st.write(f"**Action:** {log['action']}")
                st.write(f"**Details:** {log['details']}")
                st.write(f"**Timestamp:** {timestamp}")
                st.write(f"**IP Address:** {log.get('ip_address', 'Unknown')}")
    
    def generate_reports(self):
        """Generate and download reports"""
        st.title("📄 Generate Reports")
        st.caption("Create comprehensive PDF reports with filtering options")
        
        user = st.session_state.user
        role = user.get('role')
        
        grievances = self.db.get_all_grievances(role, str(user['_id']))
        
        if not grievances:
            st.info("📭 No data available to generate reports.")
            return
        
        st.write(f"📊 Total available cases: **{len(grievances)}**")
        
        # Report configuration
        st.subheader("⚙️ Report Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_type = st.selectbox("Report Type", [
                "Comprehensive Report",
                "Summary Report",
                "Status-wise Report",
                "Category-wise Report"
            ])
            
            date_range = st.selectbox("Date Range", [
                "All Time",
                "Last 7 Days",
                "Last 30 Days",
                "Last 90 Days",
                "This Year",
                "Custom Range"
            ])
            
            if date_range == "Custom Range":
                col_a, col_b = st.columns(2)
                with col_a:
                    start_date = st.date_input("From Date")
                with col_b:
                    end_date = st.date_input("To Date")
        
        with col2:
            status_filter = st.multiselect(
                "Include Status",
                Config.STATUS_OPTIONS,
                default=Config.STATUS_OPTIONS
            )
            
            priority_filter = st.multiselect(
                "Include Priority",
                Config.PRIORITY_LEVELS,
                default=Config.PRIORITY_LEVELS
            )
            
            category_filter = st.multiselect(
                "Include Categories",
                Config.CATEGORIES,
                default=[],
                help="Leave empty to include all categories"
            )
        
        # Filter grievances
        filtered_grievances = grievances
        
        # Date filtering
        if date_range != "All Time":
            if date_range == "Custom Range":
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())
            else:
                days_map = {
                    "Last 7 Days": 7,
                    "Last 30 Days": 30,
                    "Last 90 Days": 90
                }
                if date_range in days_map:
                    cutoff_date = datetime.now() - timedelta(days=days_map[date_range])
                    filtered_grievances = [g for g in filtered_grievances if g.get('created_at', datetime.now()) > cutoff_date]
                elif date_range == "This Year":
                    current_year = datetime.now().year
                    filtered_grievances = [g for g in filtered_grievances if g.get('created_at', datetime.now()).year == current_year]
        
        # Status, priority, category filtering
        if status_filter:
            filtered_grievances = [g for g in filtered_grievances if g.get('status') in status_filter]
        if priority_filter:
            filtered_grievances = [g for g in filtered_grievances if g.get('priority') in priority_filter]
        if category_filter:
            filtered_grievances = [g for g in filtered_grievances if g.get('category') in category_filter]
        
        st.write(f"📋 Filtered cases for report: **{len(filtered_grievances)}**")
        
        st.markdown("---")
        
        # Generate report
        if st.button("📥 Generate PDF Report", type="primary", use_container_width=True):
            if not filtered_grievances:
                st.warning("⚠️ No cases match the selected filters.")
                return
            
            try:
                with st.spinner("📄 Generating PDF report..."):
                    # Calculate statistics
                    stats = {
                        'total_cases': len(filtered_grievances),
                        'open_cases': len([g for g in filtered_grievances if g.get('status') == 'Open']),
                        'in_progress': len([g for g in filtered_grievances if g.get('status') == 'In Progress']),
                        'resolved_cases': len([g for g in filtered_grievances if g.get('status') == 'Resolved']),
                        'closed_cases': len([g for g in filtered_grievances if g.get('status') == 'Closed']),
                        'critical_cases': len([g for g in filtered_grievances if g.get('priority') == 'Critical']),
                        'resolution_rate': 0
                    }
                    
                    if stats['total_cases'] > 0:
                        stats['resolution_rate'] = (stats['resolved_cases'] / stats['total_cases']) * 100
                    
                    pdf_buffer = self.pdf_generator.create_grievance_report(
                        filtered_grievances,
                        stats
                    )
                    
                    filename = f"police_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    
                    st.download_button(
                        label="📥 Download Report PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    st.success("✅ Report generated successfully!")
                    st.info(f"📁 **Filename:** {filename}")
                    
            except Exception as e:
                st.error(f"❌ Error generating report: {str(e)}")
    
    def export_data(self):
        """Export data to CSV"""
        st.title("📤 Export Data")
        st.caption("Export grievance data to CSV format")
        
        user = st.session_state.user
        role = user.get('role')
        
        grievances = self.db.get_all_grievances(role, str(user['_id']))
        
        if not grievances:
            st.info("📭 No data available to export.")
            return
        
        st.write(f"📊 Total available cases: **{len(grievances)}**")
        
        # Export options
        col1, col2 = st.columns(2)
        
        with col1:
            export_format = st.selectbox("Export Format", ["CSV", "Excel (XLSX)"])
            include_all_fields = st.checkbox("Include all fields", value=True)
        
        with col2:
            date_filter = st.selectbox("Export Range", [
                "All Data",
                "Last 30 Days",
                "Last 90 Days",
                "This Year"
            ])
        
        # Filter by date
        filtered_grievances = grievances
        if date_filter != "All Data":
            days_map = {"Last 30 Days": 30, "Last 90 Days": 90}
            if date_filter in days_map:
                cutoff_date = datetime.now() - timedelta(days=days_map[date_filter])
                filtered_grievances = [g for g in filtered_grievances if g.get('created_at', datetime.now()) > cutoff_date]
            elif date_filter == "This Year":
                current_year = datetime.now().year
                filtered_grievances = [g for g in filtered_grievances if g.get('created_at', datetime.now()).year == current_year]
        
        st.write(f"📋 Cases to export: **{len(filtered_grievances)}**")
        
        if st.button("📥 Generate Export File", type="primary", use_container_width=True):
            if not filtered_grievances:
                st.warning("⚠️ No data to export.")
                return
            
            try:
                # Prepare data
                export_data = []
                for g in filtered_grievances:
                    if include_all_fields:
                        # Include all fields
                        record = {
                            'case_number': g.get('case_number', 'N/A'),
                            'title': g.get('title', ''),
                            'description': g.get('description', ''),
                            'category': g.get('category', ''),
                            'priority': g.get('priority', ''),
                            'status': g.get('status', ''),
                            'complainant_name': g.get('complainant_name', ''),
                            'complainant_phone': g.get('complainant_phone', ''),
                            'complainant_email': g.get('complainant_email', ''),
                            'location': g.get('location', ''),
                            'district': g.get('district', ''),
                            'area': g.get('area', ''),
                            'date_of_incident': g.get('date_of_incident', ''),
                            'created_at': g.get('created_at', ''),
                            'updated_at': g.get('updated_at', ''),
                            'submitted_by': g.get('submitted_by', ''),
                            'station': g.get('station', '')
                        }
                    else:
                        # Essential fields only
                        record = {
                            'case_number': g.get('case_number', 'N/A'),
                            'title': g.get('title', ''),
                            'category': g.get('category', ''),
                            'status': g.get('status', ''),
                            'priority': g.get('priority', ''),
                            'location': g.get('location', ''),
                            'date': g.get('created_at', '')
                        }
                    
                    export_data.append(record)
                
                df = pd.DataFrame(export_data)
                
                # Generate file
                if export_format == "CSV":
                    csv_data = self.csv_processor.export_to_csv(export_data)
                    filename = f"grievances_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    
                    st.download_button(
                        label="📥 Download CSV File",
                        data=csv_data,
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    # Excel export
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Grievances')
                    
                    filename = f"grievances_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    
                    st.download_button(
                        label="📥 Download Excel File",
                        data=output.getvalue(),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
                st.success(f"✅ Export file generated successfully!")
                st.info(f"📁 **Filename:** {filename} | **Records:** {len(export_data)}")
                
            except Exception as e:
                st.error(f"❌ Error exporting data: {str(e)}")
    
    def ai_assistant(self):
        """AI assistant for insights"""
        st.title("🤖 AI Assistant")
        st.caption("Get intelligent insights about your grievance data")
        
        if not self.ai.check_connection():
            st.error("🔴 Cannot connect to Ollama AI service.")
            st.info("""
            **To enable AI features:**
            1. Install Ollama: https://ollama.ai
            2. Run: `ollama serve`
            3. Pull a model: `ollama pull llama2`
            4. Restart this application
            """)
            return
        
        st.success("✅ Connected to Ollama AI")
        
        models = self.ai.get_available_models()
        if not models:
            st.warning("⚠️ No AI models available. Please pull a model using `ollama pull llama2`")
            return
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_model = st.selectbox("🤖 AI Model", models, index=0)
        
        with col2:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_history = []
                st.rerun()
        
        # Prepare context
        user = st.session_state.user
        role = user.get('role')
        grievances = self.db.get_all_grievances(role, str(user['_id']))
        
        if grievances:
            df = pd.DataFrame(grievances)
            context = f"""
            Police Grievance Management System Context:
            - Total Cases: {len(grievances)}
            - Open: {len(df[df['status'] == 'Open'])}
            - In Progress: {len(df[df['status'] == 'In Progress'])}
            - Resolved: {len(df[df['status'] == 'Resolved'])}
            - Top Categories: {df['category'].value_counts().head(5).to_dict()}
            - Priority Distribution: {df['priority'].value_counts().to_dict()}
            - Districts: {df['district'].value_counts().head(5).to_dict() if 'district' in df else 'N/A'}
            
            You are an AI assistant helping police officers analyze grievance data.
            Provide helpful, professional insights and recommendations.
            """
        else:
            context = "No grievance data available currently."
        
        # Display chat history
        for chat in st.session_state.chat_history:
            with st.chat_message(chat["role"]):
                st.write(chat["content"])
        
        # Chat input
        user_input = st.chat_input("💬 Ask about cases, patterns, or get recommendations...")
        
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            with st.chat_message("user"):
                st.write(user_input)
            
            with st.chat_message("assistant"):
                with st.spinner("🤖 AI is analyzing..."):
                    response = self.ai.generate_response(user_input, selected_model, context)
                    st.write(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
        
        # Suggested queries
        st.markdown("---")
        st.subheader("💡 Suggested Questions")
        
        suggestions = [
            "What are the top 3 crime categories in our data?",
            "Which areas have the most critical cases?",
            "What is our case resolution performance?",
            "Suggest improvements for reducing pending cases",
            "Identify patterns in recent complaints"
        ]
        
        cols = st.columns(len(suggestions))
        for i, suggestion in enumerate(suggestions):
            with cols[i]:
                if st.button(suggestion, key=f"suggest_{i}", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "content": suggestion})
                    st.rerun()
    
    def run(self):
        """Main application runner"""
        st.set_page_config(
            page_title="AP Police Grievance Management System",
            page_icon="🚔",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Custom CSS
        st.markdown("""
        <style>
        .stAlert {margin-top: 1rem;}
        .stMetric {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        .stExpander {
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if not st.session_state.get('authenticated'):
            self.authenticate()
        else:
            # Check for navigation override
            if 'nav_override' in st.session_state:
                choice = st.session_state.nav_override
                del st.session_state.nav_override
            else:
                choice = self.sidebar()
            
            # Route to appropriate page
            if "Dashboard" in choice:
                self.dashboard()
            elif "User Management" in choice:
                self.user_management()
            elif "All Cases" in choice or "My Cases" in choice:
                self.view_cases()
            elif "Manual Entry" in choice:
                self.manual_entry()
            elif "CSV Import" in choice:
                self.csv_import()
            elif "Analytics" in choice:
                self.show_analytics()
            elif "Location Map" in choice or "My Cases Map" in choice:
                self.show_location_map()
            elif "Crime Heatmap" in choice:
                self.show_crime_heatmap()
            elif "Case Assignment" in choice:
                self.case_assignment()
            elif "Activity Logs" in choice:
                self.activity_logs()
            elif "Generate Reports" in choice or "My Reports" in choice:
                self.generate_reports()
            elif "Export Data" in choice or "Export My Data" in choice:
                self.export_data()
            elif "AI Assistant" in choice:
                self.ai_assistant()


# ═══════════════════════════════════════════════════════════════════════════
#                         APPLICATION ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        # Test MongoDB connection
        client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        
        # Initialize and run application
        app = PoliceGrievanceApp()
        app.run()
        
    except Exception as e:
        st.error(f"🔴 Critical Error: {str(e)}")
        
        if "connection" in str(e).lower():
            st.write("**MongoDB Connection Error**")
            st.write("Please ensure MongoDB is running:")
            st.code("mongod --dbpath /path/to/data", language="bash")
            st.write("Or install MongoDB: https://www.mongodb.com/try/download/community")
        
        st.write("**Error Details:**")
        st.code(str(e))
        st.stop()
