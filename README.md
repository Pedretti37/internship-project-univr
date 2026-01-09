# Internship Project - Univr

## Project Goal
The goal of this project is to analyze organizational skill gaps and map them to educational offerings, creating a bridge between employee needs and training solutions.

## Current Features
The application is currently in the development phase. A basic Authentication System is now functional.

- **User Registration:** Users can sign up providing their info.
- **User Profile:** Users can now enter their profile and change their password, update target roles (max 5 to analyse), compare skill models of current target roles with their skills.
- **Organization Registrazion:** Organization can sign up providing their info.
- **Secure Authentication:** Passwords are never stored in plain text. The system uses **Argon2** hashing for security.
- **Login System:** Users/Orgs can log in to access their personal area.
- **Guest Access:** A "Continue as Guest" mode allows limited access to the platform for non-registered users.
- **Data Storage:** Currently using a lightweight JSON-based file system for user/orgs management. EXCEL file added for reading roles/function and their descriptions.
- **LLM:** Use of Gemini AI with API to associate skill models to target roles set by users and elaborate skill gap.

## Tech Stack
- **Backend:** Python, FastAPI
- **Data Validation:** Pydantic
- **Security:** Passlib (Argon2-cffi)
- **Frontend:** HTML5, CSS3, Jinja2 Templates
- **Server:** Uvicorn

## Project Structure
- `main.py`: Application entry point.
- `routes/`: Route definitions.
- `config.py`: Project main configuration file.
- `crud.py`: Handles file I/O operations (JSON reading/writing and EXCEL).
- `models.py`: Pydantic models for data validation and structure.
- `data/`: Directory containing JSON and EXCEL files.
- `static/`: CSS.
- `templates/`: HTML templates.
- `dependencies.py`: File used for getting current User/Org.
- `llm/`: Directory containing Gemini API and the possibility to search for AI models.

## How to Run
1.  **Clone the repository.**
2.  **Configure Gemini API**  
    To enable AI features, you need a valid Google API Key.
    * Get your free API Key here: [Google AI Studio](https://aistudio.google.com/app/apikey)
    * Open `llm/gemini.py`.
    * Find the line `API_KEY = "CURRENT_KEY"` and replace `"CURRENT_KEY"` with your actual API key.
3.  **Create & Activate venv (optional):**
    ```bash
    python -m venv venv
    ```
    ```bash
    # Attiva env (Windows)
    venv\Scripts\activate
    ```
    ```bash
    # Attiva env (Mac/Linux)
    source venv/bin/activate
    ```
4.  **Install requirements:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Start the server:**
    ```bash
    uvicorn main:app --reload
    ```
6.  Open browser at `http://127.0.0.1:8000`
