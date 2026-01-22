# Skill Gap Analysis Platform - Internship Project @ Univr

## Project Goal
The primary goal of this project is to bridge the gap between employee skills and organizational needs. The platform analyzes **organizational skill gaps** by mapping current employee competencies against target roles and suggests educational offerings to fill those gaps.

## Current Features
The application is currently in the **development phase**.

### User Module
- **User Registration & Login:** Secure sign-up and authentication system.
- **Profile Management:** Users can update personal info and change passwords.
- **Skill Modeling:** Users can build their profile by importing standardized skills from the **ESCO API**.
- **Target Roles:** Users can define up to 5 target roles to track their career path.
- **Skill Forecast by CEDEFOP:** Users can now see whether their target roles are growing/declining occupation-wise per country.
- **Skill Gap Evaluation:** Users can evaluate the skill gap between their current skill set and target roles.

### Organization Module
- **Organization Registration:** Companies can sign up and create a business profile.
- **Team Management:** Organizations can add existing users to their workforce.
- **Project & Assessment:**
    - Create specific projects with defined goals.
    - Assign employees to projects.
    - Define **Target Roles** (from ESCO) for the project.
    - *(Coming Soon)*: Calculate the skill gap between the team's current skills and the project's target roles.

### Core Features
- **Secure Authentication:** Passwords are hashed using **Argon2** (via Passlib) and never stored in plain text.
- **Data Storage:** Lightweight JSON-based file system for easy prototyping of Users, Organizations, and Projects.
- **ESCO API Integration:** Real-time fetching of occupations and skills from the European Skills/Competences classification.
- **Guest Access:** Limited "Continue as Guest" mode for platform exploration.

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.10+, FastAPI |
| **Server** | Uvicorn |
| **Validation** | Pydantic |
| **Security** | Passlib (Argon2-cffi) |
| **Frontend** | HTML5, CSS3, Jinja2 Templates |
| **External APIs** | ESCO API, Google Gemini (LLM) |

## Project Structure

```text
├── config.py           # Main configuration settings
├── dependencies.py     # Dependency injection (Current User/Org retrieval)
├── main.py             # Application entry point
├── requirements.txt    # Python dependencies
│
├── crud/               # JSON I/O operations (Database layer)
├── data/               # JSON Storage (Users, Orgs, Projects) and CEDEFOP database
├── esco/               # ESCO API integration logic
├── models.py           # Pydantic data models
├── routers/            # Endpoints (User, Org, etc.)
│
├── static/             # CSS and static assets
└── templates/          # HTML Jinja2 templates
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
    uvicorn main:app --reload
    ```
5.  Open browser at `http://127.0.0.1:8000`
