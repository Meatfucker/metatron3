@echo off
:: Name of the virtual environment folder
set VENV_DIR=venv

:: Activate the virtual environment
call %VENV_DIR%\Scripts\activate.bat

:: Run the Uvicorn server
python metatron3.py