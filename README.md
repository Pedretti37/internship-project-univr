# Internship Project - Univr

## Project Goal
The goal of this project is to analyze organizational skill gaps and map them to educational offerings, creating a bridge between employee needs and training solutions.

## Current Features
The application is currently in the development phase. A basic Authentication System is now functional.

- **User Registration:** Users can sign up providing Name, Surname, Username, and Password.
- **Secure Authentication:** Passwords are never stored in plain text. The system uses **Argon2** hashing for security.
- **Login System:** Users can log in to access their personal area.
- **Guest Access:** A "Continue as Guest" mode allows limited access to the platform for non-registered users.
- **Data Storage:** Currently using a lightweight JSON-based file system for user management.

## Tech Stack
- **Backend:** Python, FastAPI
- **Data Validation:** Pydantic
- **Security:** Passlib (Argon2-cffi)
- **Frontend:** HTML5, CSS3, Jinja2 Templates
- **Server:** Uvicorn

## Project Structure
- `main.py`: Application entry point and route definitions.
- `crud.py`: Handles file I/O operations (JSON reading/writing).
- `models.py`: Pydantic models for data validation and structure.
- `data/`: Directory containing JSON files (User database).
- `static/`: CSS.
- `templates/`: HTML templates.

## How to Run
1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Start the server:
    ```bash
    uvicorn main:app --reload
    ```
4.  Open browser at `http://127.0.0.1:8000`
