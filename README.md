# MathExprWeb

Symbolic math web app (Flask + SymPy).  
Features: expand, simplify, factor, substitute, integrate, live LaTeX preview.

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
