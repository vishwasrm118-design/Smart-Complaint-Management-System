# SMART COMPLAINT MANAGEMENT SYSTEM

## Team Members

1. **Spoorthi P** — PES1UG24CS629
2. **Vishwas R** — PES1UG24CS644
3. **S H Purvik Gowda** — PES1UG25CS838

---

## Project Overview

The Smart Complaint Management System (SCMS) is a web-based application designed to simplify complaint registration, tracking, management, and resolution.

The system provides a centralized platform where users can submit complaints, monitor their progress, view complaint history, and provide feedback. Administrators can manage complaints, update their statuses, and handle the resolution process.

The application also supports assisted complaint registration, allowing administrators to lodge complaints on behalf of individuals who need assistance accessing the portal.

## Objectives

- Provide a simple and accessible complaint registration platform.
- Generate unique identifiers for submitted complaints.
- Allow users to track complaint progress.
- Enable administrators to manage and resolve complaints.
- Maintain complaint history for better tracking and accountability.
- Provide notifications and feedback functionality.
- Improve transparency and organization in complaint management.

## Features

### 1. User Registration and Authentication
- New users can register through the registration form.
- Existing users can log in using their credentials.
- Protected pages require authentication.
- Functionalities are provided based on user roles.

### 2. Complaint Registration
- Users can submit complaints through an online form.
- Complaint details include title, description, and category.
- The system generates a unique complaint ID.
- Submitted complaints are stored in the database.

### 3. Complaint Tracking
- Users can track complaints using their complaint IDs.
- Users can view the current status of their complaints.
- Search and filtering options help locate specific complaints.

### 4. Complaint History
- Users can view previously submitted complaints.
- Complaint history provides information about complaint progress and status.
- Users can search and filter their complaint records.

### 5. Admin Dashboard
Administrators have access to complaint-management functionalities, including:
- Viewing complaints submitted through the system.
- Monitoring complaint statistics.
- Accessing complaint management features.
- Managing the complaint-handling process.

### 6. Assisted Complaint Registration
Administrators can use the complaint registration functionality to assist individuals who cannot independently access or operate the online portal.

For example, if a resident visits an administrative office to report a water leakage issue, the administrator can enter the complaint into the system on their behalf.

### 7. Complaint Status Management

Administrators can update complaint statuses as complaints progress through the handling process.

The application uses the following statuses:

- **Submitted** – Complaint has been registered.
- **In Progress** – Complaint is being addressed.
- **Resolved** – Complaint has been successfully addressed.
- **Rejected** – Complaint has not been accepted for resolution.

### 8. Complaint Resolution
- Administrators can manage the complaint resolution process.
- Resolution remarks can communicate how a complaint was addressed.
- Users can refer to complaint information to understand its progress.

### 9. Notifications
The application includes a notification feature to communicate complaint-related updates to users.

### 10. Feedback Management
- Users can submit feedback regarding the complaint-handling process.
- Users can view their feedback history.

---

## User Roles

| Functionality | User | Administrator |
|---|---|---|
| Register an account | Yes | Admin account configured separately |
| Login | Yes | Yes |
| Lodge a complaint | Yes | Yes, for assisted registration |
| View own complaint history | Yes | Yes |
| Submit feedback | Yes | Available through shared functionality |
| View all complaints | No | Yes |
| Manage complaint statuses | No | Yes |
| Manage complaint resolution | No | Yes |
| Access admin dashboard | No | Yes |

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming language |
| Flask | Web application framework |
| SQLite | Database management |
| HTML5 | Webpage structure |
| CSS3 | Styling and layout |
| JavaScript | Client-side interactions |
| Jinja2 | Dynamic HTML templating |
| Pytest | Automated testing |
| Git and GitHub | Version control and collaboration |

---

## System Workflow

1. A user registers and logs into the application.
2. The user submits a complaint through the complaint registration form.
3. The system generates a unique complaint ID.
4. The complaint is stored in the SQLite database.
5. The administrator views the complaint through the admin dashboard.
6. The administrator updates the complaint status as necessary.
7. The administrator handles the resolution process and provides remarks.
8. The user tracks the complaint and views its history.
9. The user can submit feedback regarding the complaint-handling process.

---

## Project Structure

```text
Smart-Complaint-Management-System/
│
├── app.py
├── requirements.txt
├── complaints.db
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── complaint_history.html
│   └── ...
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── tests/
│   └── test_app.py
│
├── Documents/
│   ├── SRS.docx
│   ├── TestPlan.docx
│   ├── UseCaseDiagram.pdf
│   └── UseCaseFlow.docx
│
└── README.md
```

*Note: This is an illustrative structure. Actual filenames and folders may differ in the repository.*

---

## Installation and Setup

### Prerequisites

- Python 3.x
- Git
- Visual Studio Code (recommended)
- A web browser

### Step 1: Clone the Repository

```bash
git clone https://github.com/vishwasrm118-design/Smart-Complaint-Management-System.git
```

### Step 2: Navigate to the Project Directory

```bash
cd Smart-Complaint-Management-System
```

### Step 3: Create a Virtual Environment

```bash
python3 -m venv .venv
```

### Step 4: Activate the Virtual Environment

For macOS/Linux:

```bash
source .venv/bin/activate
```

For Windows:

```bash
.venv\Scripts\activate
```

### Step 5: Install Dependencies

```bash
python -m pip install -r requirements.txt
```

---

## Running the Application

Start the Flask application:

```bash
python app.py
```

Open your browser and navigate to:

```text
http://127.0.0.1:5000
```

The application should now be accessible locally.

To stop the application, press `Ctrl + C` in the terminal.

---

## Testing

The project uses Pytest for automated testing.

Run the test suite using:

```bash
python -m pytest -v
```

This executes the available automated tests and displays the results in the terminal.

### Test Coverage

Code coverage can be measured using `pytest-cov`.

Install the package if required:

```bash
python -m pip install pytest-cov
```

Run the coverage command:

```bash
python -m pytest --cov=app --cov-branch --cov-report=term-missing --cov-report=html
```

This generates:

- Statement coverage information.
- Branch coverage information.
- A list of uncovered lines.
- An HTML coverage report in the `htmlcov/` directory.

Open `htmlcov/index.html` in a browser to inspect the coverage report.

---

## Project Development

The project was developed incrementally using an Agile-inspired Sprint approach.

### Sprint 1 – Core Application Development

The first sprint focused on developing the basic complaint management functionality.

Key activities included:

- Setting up the Flask application.
- Implementing user registration and login.
- Developing the user dashboard.
- Implementing complaint registration.
- Generating unique complaint IDs.
- Implementing basic complaint tracking.
- Creating the initial database structure.

### Sprint 2 – Complaint Management and Resolution

The second sprint focused on extending the application with additional complaint-management capabilities.

Key activities included:

- Implementing complaint history.
- Developing administrator complaint management functionality.
- Implementing complaint status management.
- Supporting the complaint resolution process.
- Adding resolution remarks.
- Developing feedback functionality.
- Improving the user interface and application workflow.
- Performing functional and automated testing.

### Version Control and Collaboration

Git and GitHub were used to manage project source code and support team collaboration.

The project used feature branches and pull requests to organize development work.

The integration branch was used to combine team changes before integrating completed work into the main branch.

---

## Future Enhancements

The following improvements can be considered for future versions:

- Email and SMS notifications for complaint updates.
- File and image attachments during complaint registration.
- Improved role-based access control.
- Separate resident details and administrator details for assisted complaint registration.
- Complaint priority classification.
- Advanced complaint analytics and reporting.
- Improved search and filtering functionality.
- Deployment to a cloud hosting platform.
- Enhanced security and performance.

---

## Conclusion

The Smart Complaint Management System provides a centralized platform for complaint registration, tracking, administration, and resolution. By providing dedicated user and administrator functionalities, the application aims to make complaint handling more organized, transparent, and efficient.
