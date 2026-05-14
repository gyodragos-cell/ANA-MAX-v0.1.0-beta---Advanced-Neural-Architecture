# 🚀 ANA MAX - Setup și Rulare

## Quick Start (5 minute)

### 1. Instalare Prerequisites
```powershell
# Python 3.11+
python --version

# npm (pentru VS Code extension - optional)
npm --version
```

### 2. Clone și Setup
```powershell
git clone https://github.com/YOUR_USERNAME/ana-max.git
cd ana-max

# Creeaza virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Instaleaza dependente
pip install -r requirements.txt
```

### 3. Configureaza Environment
```powershell
# Copiaza template-ul
copy .env.example .env

# Editeaza .env cu API keys (optional - merge și fără)
```

### 4. Porneste MCP Server
```powershell
python main.py
```

Server e online pe **`http://127.0.0.1:8765`**

---

## 🔨 Comenzi Disponibile

### List Tools (42 disponibile)
```powershell
python main.py --list-tools
```

### Quick Test
```powershell
python main.py --test
```

### Custom Port
```powershell
python main.py --port 9000 --host 0.0.0.0
```

### Debug Mode
```powershell
python main.py --debug
```

---

## 📡 Testare MCP via HTTP

### Health Check
```powershell
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8765/health" -UseBasicParsing
$response.Content | ConvertFrom-Json
```

### Execute Tool (exemplu)
```powershell
$body = @{
    tool = "file_operations"
    params = @{
        operation = "list"
        path = "."
    }
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:8765/execute" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body `
  -UseBasicParsing
```

---

## 🔌 VS Code Extension (Optional)

### Install local extension
1. Deschide `vscode_extension/` folder în VS Code
2. Apasă `F5` → Extension Development Host
3. Cauta: `ANA MAX: Start MCP Server`

---

## 🎯 Tools Disponibile (42)

### Core Tools
- `file_operations` - Citire, scriere, cautare fisiere
- `code_tools` - Analiză și execuție cod
- `browser_control` - Deschide și inspecteaza pagini
- `terminal` - Terminal persistent cu sesiune

### Windows Automation
- `windows_uia_bridge` - UI Automation (click, type, read)
- `system_control` - Procese, vitals, comenzi shell

### Advanced Tools
- `git_operations` - Git control
- `security_audit` - Scan secrete și vulnerabilități
- `smart_search` - Ultra-fast search în proiecte
- `codebase_understanding` - Semantic analysis

### Mobile & Pentesting
- `adb_operations` - Android device control
- `frida_instrument` - Dynamic instrumentation
- `network_pentest` - Port scan, vuln detection
- `apk_analyzer` - Reverse engineering

...și 27 mai departe. Vezi `python main.py --list-tools`

---

## 🔐 Security Notes

- `.env` conține API keys locale - **NEVER commit**
- MCP server ascultă pe `127.0.0.1` (localhost only)
- Premium tools (desktop_capture, live_viewer) sunt disabled în trial version
- Niciun tool nu face apeluri externe fără consentul tău

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'core'"
```powershell
# Asigura-te că ești în directorul corect
cd ana-max
python main.py
```

### "Port 8765 already in use"
```powershell
# Foloseste alt port
python main.py --port 8766
```

### "Python not found"
```powershell
# Instaleaza Python de la https://python.org
# Sau foloseste py launcher
py -3 main.py
```

---

## 📞 Support

- Citeaza [PROJECT_MAP_AI_GUIDE.md](docs/PROJECT_MAP_AI_GUIDE.md) pentru arhitectură
- Verifica [README.md](README.md) pentru overview complet
- Issues: github.com/YOUR_USERNAME/ana-max/issues

---

**Happy hacking! 🎯**
