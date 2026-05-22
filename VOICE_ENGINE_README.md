# ANA MAX Voice Engine – Quick Start

## What is this?
This script launches the **ANA MAX** voice engine (Edge TTS) that reads the assistant’s responses aloud.

## Prerequisites
- Python 3.12 (or later) with the packages `pyttsx3` and `edge‑tts` installed.  The repository’s `requirements.txt` already includes them; run `pip install -r requirements.txt`.
- A working audio output device and speakers.

## How to run
From the repository root, execute the launcher script located in the `scripts/` folder:

```powershell
# From the repository root
scripts\ana_voice.bat
```

The batch file changes to the correct workspace directory and starts the voice helper:

```bat
@echo off
rem ------------------------------------------------------------
rem ANA MAX Voice Engine Launcher (repository version)
rem ------------------------------------------------------------

:: Change to the ANA_MAX workspace directory (relative path)
cd /d "%~dp0..\ANA_MAX"

:: Run the voice toggle script with unbuffered output so errors appear live
python -u voice_toggle.py

:: Keep the window open after the script ends so you can see any messages
pause
```

### What you’ll hear
- A greeting: **“Voice is now on. I will speak Qoder messages while you test demos.”**
- All subsequent chat replies from the Antigravity agent will be spoken aloud.
- To stop the engine, close the console window or press **Ctrl + C**.

## Troubleshooting
- If you see `ERROR: Voice engine failed to initialise`, verify that `pyttsx3` can access the default Windows voice (Microsoft Zira) and that your speakers are not muted.
- Check the console output for stack‑trace details; copy any errors and share them in the issue tracker.

---
*This documentation is part of the public release; no private paths or user‑specific data are included.*
