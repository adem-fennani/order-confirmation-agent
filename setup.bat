@echo off
echo =================================
echo Order Confirmation Agent Setup
echo =================================

echo.
echo 1. Creating project structure...
mkdir src\api
mkdir src\agent
mkdir src\voice
mkdir src\web
mkdir tests
mkdir docs
mkdir scripts
mkdir config

echo.
echo 2. Creating initial files...
echo # Order Confirmation Agent > README.md
echo # Python > .gitignore
echo fastapi==0.104.1 > requirements.txt
echo uvicorn[standard]==0.24.0 >> requirements.txt
echo langchain-core==0.1.12 >> requirements.txt
echo pydantic==2.5.0 >> requirements.txt
echo python-multipart==0.0.6 >> requirements.txt

echo.
echo # Development dependencies > requirements-dev.txt
echo pytest==7.4.3 >> requirements-dev.txt
echo black==23.10.1 >> requirements-dev.txt
echo flake8==6.1.0 >> requirements-dev.txt
echo mypy==1.7.1 >> requirements-dev.txt

echo.
echo 3. Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

echo.
echo 4. Installing dependencies...
pip install -r requirements.txt
pip install -r requirements-dev.txt

echo.
echo 5. Creating VS Code configuration...
mkdir .vscode
echo { > .vscode\settings.json
echo     "python.defaultInterpreterPath": "./venv/Scripts/python.exe", >> .vscode\settings.json
echo     "python.testing.pytestEnabled": true, >> .vscode\settings.json
echo     "python.testing.unittestEnabled": false, >> .vscode\settings.json
echo     "python.linting.enabled": true, >> .vscode\settings.json
echo     "python.linting.pylintEnabled": true, >> .vscode\settings.json
echo     "editor.formatOnSave": true, >> .vscode\settings.json
echo     "python.formatting.provider": "black" >> .vscode\settings.json
echo } >> .vscode\settings.json

echo.
echo 6. Creating .gitignore...
echo __pycache__/ > .gitignore
echo *.py[cod] >> .gitignore
echo *$py.class >> .gitignore
echo venv/ >> .gitignore
echo .env >> .gitignore
echo .vscode/ >> .gitignore
echo *.log >> .gitignore

echo.
echo 7. Initializing Git repository...
git init
git branch -M main
git add .
git commit -m "Initial project setup"

echo.
echo =================================
echo Setup Complete!
echo =================================
echo.
echo Next steps:
echo 1. Open VS Code: code .
echo 2. Create GitHub repository
echo 3. Connect to GitHub: git remote add origin YOUR_REPO_URL
echo 4. Start coding!
echo.
pause