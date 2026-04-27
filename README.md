# Police Grievance Management System

## Overview

This repository contains a Streamlit-based Police Grievance Management System for Andhra Pradesh. The application is implemented in a single Python script, `final.py`, and provides role-based grievance tracking, analytics, and reporting functionality for police administrators, officers, and constables.

## Key Features

- Role-based sign in for Admin, Officer, and Constable
- Manual complaint/case entry with auto-generated case numbers
- Bulk CSV grievance import
- Interactive location maps with Folium
- Crime density heatmaps
- Analytics dashboard and charts with Plotly
- PDF report generation using ReportLab
- Activity audit logs and case assignment workflow
- Data export capabilities
- Search and advanced filtering
- Optional AI assistant integration via Ollama

## Technology Stack

- Frontend: Streamlit
- Database: MongoDB
- Visualization: Plotly, Folium
- Geocoding: GeoPy
- PDF export: ReportLab
- Optional AI integration: Ollama

## Requirements

- Python 3.10+
- MongoDB community server
- Streamlit
- Required Python packages:
  - streamlit
  - pandas
  - numpy
  - pymongo
  - bcrypt
  - plotly
  - reportlab
  - chardet
  - requests
  - folium
  - streamlit-folium
  - geopy
  - bson

## Installation

1. Install Python 3.10 or newer.
2. Install MongoDB and start the MongoDB server.
3. Create and activate a virtual environment (recommended):

```bash
python -m venv venv
venv\Scripts\activate
```

4. Install dependencies:

```bash
pip install streamlit pandas numpy pymongo bcrypt plotly reportlab chardet requests folium streamlit-folium geopy bson
```

## Configuration

The application uses environment variables for MongoDB and optional AI settings. Defaults are provided inside the script.

- `MONGO_URI`: MongoDB connection string (default: `mongodb://localhost:27017/`)
- `DB_NAME`: MongoDB database name (default: `ap_police_grievance_system`)
- `OLLAMA_URL`: Ollama API URL for optional AI assistant (default: `http://localhost:11434`)

Example:

```bash
set MONGO_URI=mongodb://localhost:27017/
set DB_NAME=ap_police_grievance_system
set OLLAMA_URL=http://localhost:11434
```

## Running the App

From the project directory, run:

```bash
streamlit run final.py
```

Open the Streamlit URL shown in the terminal to access the application.

## Default Users

The app initializes default users on first run:

- Admin
  - Username: `admin`
  - Password: `admin@2025`
- Senior Officer
  - Username: `officer1`
  - Password: `officer@2025`
- Constable
  - Username: `constable1`
  - Password: `constable@2025`

## Notes

- The app expects a running MongoDB instance before startup.
- If using the optional AI Assistant, ensure Ollama is running and reachable.
- This implementation is contained in `final.py` and does not include a separate `requirements.txt` file.

## File

- `final.py` - Main Streamlit application script containing the full system implementation.
