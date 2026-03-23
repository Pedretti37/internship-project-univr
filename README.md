# Skill Gap Analysis Platform - Internship Project @ Univr

## Project Goal
The primary goal of this project is to bridge the gap between employee/organizational skills and different functions needs.

### User Module (Individual & Manager Levels)
- **User Registration & Login:** Secure sign-up and authentication system.
- **Profile Management:** Users can update personal info and change passwords.
- **Skill Modeling:** Users can build their profile by importing standardized skills from the ESCO API or uploading MuchSkills CSV exports.
- **Target Roles:** Users can define up to 5 target roles to track their career path.
- **Market Analysis (CEDEFOP):** Users can forecast whether their target roles are growing or declining occupation-wise based on country and sector.
- **Skill Gap Evaluation:** An advanced algorithm evaluates the exact match percentage between the user's current skill set and the essential skills of their target roles.
- **Project & Assessment:**
    - Create specific projects with defined goals.
    - Assign employees to projects and define Target Roles (from ESCO).
    - Automatically calculate the skill gap between the assigned team's current skills and the project requirements.
- **Learning Recommendations:** The system dynamically suggests specific learning programs (e.g., Online Courses, University Courses) targeted at the user's missing or partially matched skills.
- **Export capabilities:** Users can export their detailed Skill Gap Assessment and recommended learning plan into a formatted PDF.

### Organization Module (HR Level)
- **Organization Registration:** Companies can sign up and create a business profile.
- **Team Management:** Organizations can invite existing users, manage their workforce, and promote/revoke Manager privileges.
- **Global HR Analytics:** HR managers can run an aggregated analysis across all active projects to identify the most frequent skill shortages within the organization.
- **Strategic Corporate Training:** Based on the global gap, the system suggests "Broad Plans" (e.g., Seminars, Hands-on Sessions, Industrial Training) to upskill larger parts of the workforce simultaneously.
- **Export PDF:** HR can download the aggregated organizational forecast and strategic training recommendations as a PDF report.
- **Educational Data Management (CRUD):** Organizations can act as course providers. They can Create, Read, Update, and Delete internal or external educational offerings, mapping them to specific ESCO skills and toggling Public/Private access.

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.10+, FastAPI |
| **Server** | Uvicorn |
| **Validation** | Pydantic |
| **Security** | Passlib (Argon2-cffi) |
| **Frontend** | HTML5, CSS3, Jinja2 Templates |
| **External APIs** | ESCO API |

## Project Structure

```text
intership-project-univr/
|
├── app/
|    ├── main.py                     # Application entry point
|    ├── service/                    # Main configuration settings
|    ├── crud/                       # JSON I/O operations (Database layer)
|    ├── educational_offerings/      # Educational Courses recommendation
|    ├── esco/                       # ESCO API integration logic
|    ├── models.py                   # Pydantic data models
|    ├── routers/                    # Endpoints (User, Org, etc.)
|    ├── static/                     # CSS and static assets (.csv template)
|    └── templates/                  # HTML Jinja2 templates
|
├── data/                            # JSON Storage (Users, Orgs, Projects)
|    ├── cedefop/                    # CEDEFOP database
|    ├── invitations/                
|    ├── organizations/                   
|    └── users/                   
|
├── tests/                           # Test files
├── pytest.ini                       # Configuration file for tests 
|
└── requirements.txt                 # Python dependencies


```

## How to Run
1.  **Clone the repository.**
2.  **Create & Activate venv (optional):**
    ```bash
    python -m venv venv
    ```
    ```bash
    # Attiva env (Windows)
    .\venv\Scripts\activate
    ```
    ```bash
    # Attiva env (Mac/Linux)
    source venv/bin/activate
    ```
3.  **Install requirements:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Start the server:**
    ```bash
    uvicorn app.main:app --reload
    ```
    **For tests run this instead of starting the server:**
    ```bash
    pytest -v
    ```
5.  Open browser at `http://127.0.0.1:8000`
