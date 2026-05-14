# 📦 ANA MAX - Dependencies Guide

## ✅ Required (Installed Automatically)

These are installed by `install.bat` or `pip install -r requirements.txt`:

```bash
pip install -r requirements.txt
```

**Includes:**
- Flask, requests, pydantic (MCP Server)
- pywinauto, psutil (Desktop Automation)
- selenium, beautifulsoup4 (Web & Browser)
- watchdog, chardet (Code Intelligence)
- frida, cryptography (Security Tools)
- pyyaml, colorama, Pillow (Utilities)
- **pywin32** (Window & Clipboard Management)
- **mss** (Screenshots for OCR)

---

## 🎯 Optional Dependencies

### 1. **OCR Support** (Choose ONE)

#### Option A: PaddleOCR (Recommended - More Accurate)
```bash
pip install paddleocr paddlepaddle
```
- ✅ More accurate
- ✅ Better for complex layouts
- ⚠️ First run downloads ~100MB models
- ⚠️ Slower on CPU (~2-5 sec per screenshot)

#### Option B: Tesseract (Faster, Lighter)
```bash
pip install pytesseract
```
- ⚠️ Requires Tesseract.exe installed separately
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Add to PATH after installation

---

### 2. **Voice & Notifications** (Context Engine)

For JARVIS-like voice and Windows notifications:

```bash
pip install pyttsx3 win10toast
```

- **pyttsx3**: Text-to-speech voice (offline)
- **win10toast**: Beautiful Windows 10/11 toast notifications

---

### 3. **Android Tools** (Optional)

**ADB** (Android Debug Bridge):
- Download from: https://developer.android.com/studio/releases/platform-tools
- Add to PATH

**Frida** (already in requirements.txt):
- ⚠️ Requires Visual C++ Build Tools
- Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- Install "Desktop development with C++" workload

---

## 🔒 Premium Features

### Desktop Eyes (God View)
- **Status:** Premium (disabled in trial)
- **Dependencies:** Already included (psutil, frida)
- **Activation:** Uncomment line 237 in `main.py` (requires Pro license)

---

## 🚀 Quick Setup

### Minimal Setup (51 Tools)
```bash
install.bat
```

### Full Setup (with OCR + Voice)
```bash
install.bat
pip install paddleocr paddlepaddle
pip install pyttsx3 win10toast
```

---

## ❓ Troubleshooting

### Frida Installation Fails
```
ERROR: Could not build wheels for frida
```
**Solution:** Install Visual C++ Build Tools

### PaddleOCR Too Slow
- Use `use_angle_cls=False` in ocr_tool.py (already set)
- Consider switching to Tesseract for faster results

### Tesseract Not Found
**Solution:** Add Tesseract to PATH:
```powershell
[Environment]::SetEnvironmentVariable(
    "Path", 
    $env:Path + ";C:\Program Files\Tesseract-OCR", 
    "Machine"
)
```

---

## 📊 Feature Matrix

| Feature | Minimal | Full | Premium |
|---------|---------|------|---------|
| 51 MCP Tools | ✅ | ✅ | ✅ |
| AI Core (9 tools) | ✅ | ✅ | ✅ |
| Desktop Control | ✅ | ✅ | ✅ |
| OCR | ❌ | ✅ | ✅ |
| Voice/Notifications | ❌ | ✅ | ✅ |
| Desktop Eyes (God View) | ❌ | ❌ | ✅ |

---

**Version:** 0.1.0-beta  
**Last Updated:** 2026-05-15
