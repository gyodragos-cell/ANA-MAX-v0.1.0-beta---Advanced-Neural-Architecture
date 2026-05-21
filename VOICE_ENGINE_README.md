# ANA MAX Voice Engine – Quick Start

## What is this?
This repository contains the **ANA MAX** voice engine (Edge TTS) that reads the assistant's responses aloud.

## Prerequisites
- Python 3.12 (used in the development workspace).
- Install the required Python packages:

```powershell
cd "C:\Users\billy\Desktop\ANA_MAX_GitHub_Release"
python -m venv venv   # create a virtual environment (optional but recommended)
.\venv\Scripts\activate   # PowerShell
pip install -r requirements.txt
```

The `requirements.txt` already includes the needed TTS libraries:
- `pyttsx3==2.7.2`
- `edge-tts==1.5.1`

## How to run the voice engine
1. In the release folder, double‑click the **`ana_antigravity_voice.bat`** file (or run it from a console):
   ```powershell
   .\ana_antigravity_voice.bat
   ```
2. A console window will appear, showing the engine startup logs and saying **"Voice is now on..."**.
3. While the window stays open you will hear every chat reply spoken aloud.
4. To stop the engine, close the console window or press **Ctrl + C**.

## Where is the batch file?
The batch file is created on your Desktop (`C:\Users\billy\Desktop\ana_antigravity_voice.bat`). You can copy it into this repository if you prefer a single‑folder deployment.

## History
- Added `pyttsx3` and `edge-tts` to `requirements.txt`.
- Provided a ready‑to‑run batch launcher.
- Documented usage for end‑users.

---
*Generated automatically by Antigravity agent.*
