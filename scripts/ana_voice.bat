@echo off
rem ------------------------------------------------------------
rem ANA MAX Voice Engine Launcher
rem ------------------------------------------------------------

:: Change to the ANA_MAX workspace directory
cd /d "C:\Users\billy\Desktop\ana_dev\ANA_MAX"

:: Run the voice toggle script with unbuffered output so errors appear live
python -u voice_toggle.py

:: Keep the window open after the script ends so you can see any messages
pause
