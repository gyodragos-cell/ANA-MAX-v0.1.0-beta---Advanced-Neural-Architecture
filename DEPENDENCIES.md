# ANA MAX Dependencies Guide

Install the required Python packages from the repository root:

Public repository:

```text
https://github.com/gyodragos-cell/ANA-MAX-v0.1.0-beta---Advanced-Neural-Architecture
```

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Required Runtime Groups

- MCP server: Flask, requests, pydantic
- Windows automation: pywinauto, pywin32, psutil
- Browser and web helpers: selenium, beautifulsoup4
- Code and file utilities: watchdog, chardet, pyyaml, colorama
- Vision helpers: Pillow, mss
- Security and instrumentation: cryptography, frida

## Optional OCR

PaddleOCR:

```powershell
pip install paddleocr paddlepaddle
```

Tesseract:

```powershell
pip install pytesseract
```

Tesseract also needs the Windows executable:

```text
https://github.com/UB-Mannheim/tesseract/wiki
```

## Optional Voice

```powershell
pip install pyttsx3 win10toast
```

The release-safe `edge_tts_voice` tool reports disabled cleanly if optional TTS
dependencies are not available.

## Optional Android And Frida

ADB:

```text
https://developer.android.com/studio/releases/platform-tools
```

Frida on Windows may need Microsoft Visual C++ Build Tools:

```text
https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

Use Frida only for authorized runtime instrumentation when static inspection is
not enough.

## Public Baseline

```text
64 loaded tools
4 premium-gated desktop control tools
9 AI Core adapters
desktop_capture is free Vision AI
```

Verify:

```powershell
python main.py --test
python main.py --list-tools
python -m unittest discover -s tests -v
```

For setup steps, see `SETUP_AND_RUN.md`.
