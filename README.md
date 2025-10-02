# MathExprWeb: Advanced Symbolic Calculator

This is a powerful symbolic math web application built using Flask and SymPy. It features a responsive, modern glassmorphism interface and now includes a full user authentication system for persisting calculation history.

## ✨ Features

The calculator supports a comprehensive range of algebraic and calculus operations, coupled with a robust user account system.

### User Accounts & History

* **User Registration:** New users can create a secure account.
* **Login/Logout:** A complete session management system.
* **Persistent History:** All calculations are automatically saved to the logged-in user's account and are restored upon login, providing a seamless experience across sessions.

### Core Mathematics

* **Algebraic:** Expand, Simplify, Factor, Substitute.
* **Calculus:** Integrate (Indefinite & Definite), Differentiate (Nth-order derivatives).
* **Integral Transforms:** Laplace Transform, Fourier Transform, Mellin Transform.
* **Utility:** Re-Simplify previous results (accessible in the result section).

### UI/UX

* **Modern Design:** A responsive, glassmorphism-themed UI that works on all devices.
* **Dynamic Effects:** Features an animated, glowing border on the active input field and other subtle hover effects.
* **Live Input Preview:** Instantly renders the mathematical expression from the input field as you type using KaTeX.
* **Live Result Rendering:** Renders calculation results beautifully using KaTeX.
* **Theme Toggling:** Instantly switch between Dark (Teal/Emerald) and Light (Cherry) themes.

## 🛠️ Technology Stack

* **Backend:** Flask, Flask-SQLAlchemy, Flask-Login, Werkzeug (for security)
* **Math Engine:** SymPy
* **Frontend:** HTML5, CSS3, Vanilla JavaScript
* **Database:** SQLite

## 🚀 Run Locally

Follow these steps to get the application running on your local machine.

### 1. Create and Activate Virtual Environment

First, create a virtual environment in the project directory:
python -m venv venv
Activate the environment.

* On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

* On macOS/Linux:
source venv/bin/activate

### 2. Install Dependencies

Install all the required Python packages from the `requirements.txt` file: pip install -r requirements.txt

### 3. Run the Application

Execute the main `app.py` file. The application will start, and the SQLite database (`mathexpr.db`) will be automatically created in the root directory on the first run.

python app.py
The application will be available at `http://127.0.0.1:5000`.
