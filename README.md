# MathExprWeb: Advanced Symbolic Calculator

This is a powerful symbolic math web application built using Flask and SymPy, featuring a responsive, modern interface with theme toggling and live LaTeX rendering.

## Features

The calculator supports a comprehensive range of algebraic and calculus operations:
* **Algebraic:** Expand, Simplify, Factor, Substitute.
* **Calculus:** Integrate (Indefinite & Definite), Differentiate (Nth-order derivatives).
* **Transforms:** Laplace Transform, Fourier Transform, Mellin Transform.
* **Utility:** Re-Simplify previous results (accessible in the result section).
* **UI/UX:** Live LaTeX preview, persistent calculation history, and theme toggling.

## Run locally

1. Create virtualenv:
   `python -m venv venv`
2. Activate venv (PowerShell):
   `.\venv\Scripts\Activate.ps1` (might need to set execution policy)
3. Install deps:
   `pip install -r requirements.txt`
4. Run:
   `python app.py`

## Expose publicly (ngrok)
After running the app locally on port 5000:
`ngrok http 5000`