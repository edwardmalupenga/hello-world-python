# Student Management System

A web-based application for managing student records, marks, classes, and subjects.

## Developer

**Edward Malupenga**  
Student Number: 2025557938

## Features

- **User Authentication**: Secure login system with admin and staff roles
- **Student Management**: Add, edit, and delete student records
- **Class Management**: Create and manage classes
- **Subject Management**: Add and organize subjects
- **Marks Tracking**: Record and manage student marks by term
- **Dashboard**: Overview of system statistics
- **Reports**: Generate student performance reports
- **User Management**: Admin can manage system users

## Project Structure

```
student management system1/
├── sms_app/                 # Main application package
│   ├── __init__.py         # Package initialization
│   ├── db.py               # Database management and models
│   ├── security.py         # Password hashing and authentication
│   └── reports.py          # Report generation utilities
├── templates/              # HTML templates
│   ├── login.html          # Login page
│   ├── register.html       # User registration
│   ├── dashboard.html      # Main dashboard
│   ├── students.html       # Student listing
│   ├── student_form.html   # Add/edit student form
│   ├── marks.html          # Marks management
│   ├── classes.html        # Class listing
│   ├── class_form.html     # Add class form
│   ├── subjects.html       # Subject listing
│   ├── subject_form.html   # Add subject form
│   ├── users.html          # User management
│   ├── user_form.html      # Add user form
│   ├── reports.html        # Reports page
├── web.py                  # Flask application main file
├── test_login.py           # Login testing script
└── students.db             # SQLite database (auto-created)
```

## Requirements

- Python 3.7+
- Flask
- SQLite3

## Installation

1. Clone or download the project
2. Navigate to the project directory:
   ```bash
   cd "student management system1"
   ```

3. Install dependencies:
   ```bash
   pip install flask
   ```

## Running the Application

Start the Flask development server:

```bash
python web.py
```

The application will be available at: `http://127.0.0.1:5000`

## Default Credentials

The system creates a default admin account on first run:

- **Username**: admin
- **Password**: admin123

**Note**: Change the default password after your first login.

## Database

The application uses SQLite for data storage. The database is automatically created and migrated on startup. The database file (`students.db`) is created in the application root directory.

### Database Tables

- **users**: User accounts with authentication credentials
- **classes**: Student classes/levels
- **students**: Student records
- **subjects**: Course subjects
- **marks**: Student marks/grades by term

## Key Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Redirect to dashboard or login |
| `/login` | GET, POST | User login |
| `/register` | GET, POST | Register new staff account |
| `/dashboard` | GET | Dashboard overview |
| `/students` | GET | List all students |
| `/students/add` | GET, POST | Add new student |
| `/students/edit/<sid>` | GET, POST | Edit student |
| `/students/delete/<sid>` | GET | Delete student |
| `/marks` | GET | View marks |
| `/marks/add` | POST | Add mark |
| `/classes` | GET | List classes |
| `/classes/add` | GET, POST | Add class |
| `/subjects` | GET | List subjects |
| `/subjects/add` | GET, POST | Add subject |
| `/users` | GET | List users (admin only) |
| `/users/add` | GET, POST | Add user (admin only) |
| `/users/delete/<uid>` | GET | Delete user (admin only) |
| `/reports` | GET | View reports |
| `/reports/generate/<sid>` | GET | Generate student report |
| `/logout` | GET | Logout user |

## Security Features

- Password hashing using PBKDF2-SHA256
- Session-based authentication
- Role-based access control (admin/staff)
- SQL injection prevention with parameterized queries
- CSRF protection through Flask sessions

## Configuration

The application secret key can be set via the `SECRET_KEY` environment variable:

```bash
export SECRET_KEY="your-secret-key-here"
```

If not set, a development key is used by default.

## Testing

A test script is included to verify login functionality:

```bash
python test_login.py
```

This script tests the authentication flow and validates session handling.

## Notes

- The application uses SQLite's WAL (Write-Ahead Logging) mode for better concurrency
- If the database is locked, the application will fall back to a separate database file
- Default admin account is created automatically on first run
- Student marks are stored per term with grades calculated based on marks

## License

This is an educational project for student management.

---

**Last Updated**: March 19, 2026
