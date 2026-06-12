#  Integrare Tool-uri Noi in ANA MAX

## Fisiere generate
- `tools/window_manager.py`     Window Management
- `tools/clipboard_manager.py`   Clipboard Intelligence  
- `tools/ocr_tool.py`            OCR cu PaddleOCR

---

## Pasul 1 - Copiaza fisierele in `tools/`
Pune toate cele 3 fisiere in folderul `tools/` al proiectului.

---

## Pasul 2 - Inregistreaza in `tools/__init__.py`
Adauga la sfarsitul fisierului:

```python
from .window_manager   import run as window_manager_run
from .clipboard_manager import run as clipboard_manager_run
from .ocr_tool          import run as ocr_tool_run
```

---

## Pasul 3 - Inregistreaza in `main.py`
Gaseste array-ul `desktop_tools` sau `new_tools` si adauga:

```python
{
    "name": "window_manager",
    "description": "Gestionare ferestre: listare, snap, move, tile, focus",
    "handler": window_manager_run,
},
{
    "name": "clipboard_manager",
    "description": "Clipboard: citire, scriere, istoric, monitorizare, transformari",
    "handler": clipboard_manager_run,
},
{
    "name": "ocr_tool",
    "description": "OCR pe ecran, regiune, fisier sau clipboard (PaddleOCR/Tesseract)",
    "handler": ocr_tool_run,
},
```

---

## Pasul 4 - Instalare dependente

```bash
# Activeaza venv-ul mai intai!
.\venv\Scripts\Activate.ps1

# Window Manager - fara dependente noi (Win32 nativ)

# Clipboard Manager - fara dependente noi (Win32 nativ + threading stdlib)

# OCR Tool - alege una:
pip install paddleocr paddlepaddle pillow   # recomandat (mai precis)
# SAU
pip install pytesseract pillow              # + instaleaza Tesseract OCR separat
```

---

## Pasul 5 - Test rapid

```bash
python main.py --test
```

---

## Exemple de utilizare prin MCP

### Window Manager
```json
{"tool": "window_manager", "args": {"action": "list"}}
{"tool": "window_manager", "args": {"action": "snap", "title": "Chrome", "position": "left"}}
{"tool": "window_manager", "args": {"action": "tile", "layout": "grid"}}
{"tool": "window_manager", "args": {"action": "focus", "title": "Notepad"}}
```

### Clipboard Manager
```json
{"tool": "clipboard_manager", "args": {"action": "get"}}
{"tool": "clipboard_manager", "args": {"action": "set", "text": "Hello ANA!"}}
{"tool": "clipboard_manager", "args": {"action": "history", "limit": 5}}
{"tool": "clipboard_manager", "args": {"action": "transform", "operation": "upper"}}
{"tool": "clipboard_manager", "args": {"action": "start_monitor"}}
```

### OCR Tool
```json
{"tool": "ocr_tool", "args": {"action": "check"}}
{"tool": "ocr_tool", "args": {"action": "screen"}}
{"tool": "ocr_tool", "args": {"action": "screen", "x": 0, "y": 0, "width": 800, "height": 600}}
{"tool": "ocr_tool", "args": {"action": "file", "image_path": "C:\\screenshot.png"}}
{"tool": "ocr_tool", "args": {"action": "clipboard"}}
```

---

## Note importante

- **window_manager.py** - zero dependente noi, merge imediat
- **clipboard_manager.py** - zero dependente noi, merge imediat
- **ocr_tool.py** - necesita `pip install paddleocr paddlepaddle pillow`
  - Prima rulare descarca modelele (~100MB), dupa aceea e offline
  - Pe CPU modest: ~2-5 secunde per screenshot, acceptabil
  - `use_angle_cls=False`  mai rapid, suficient pentru text drept pe ecran
