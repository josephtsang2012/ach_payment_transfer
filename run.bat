@echo off
title HSBC Pain (DO NOT CLOSE THIS WINDOW)

:: Move into the folder where this batch file lives
cd /d "%~dp0"

:: Activate the local virtual environment and run the app
call venv\Scripts\activate.bat
venv\Scripts\python.exe app.py