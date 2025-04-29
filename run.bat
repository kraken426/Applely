@echo off
python src\main.py
if errorlevel 1 exit /b %errorlevel%
python src\bounce_handler_gmail_api.py
if errorlevel 1 exit /b %errorlevel%
echo All done!
