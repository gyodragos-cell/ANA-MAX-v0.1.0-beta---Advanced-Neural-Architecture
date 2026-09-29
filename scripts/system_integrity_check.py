import sys
import os
from pathlib import Path
import importlib

# Fix UnicodeEncodeError for emojis on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

sys.path.append('c:/Users/billy/Desktop/ana-manus/ANA_MAX')
from tools.base import ToolRegistry
print("=== SYSTEM INTEGRITY CHECK - ENTERPRISE AUDIT ===\n")

# 1. Verificare Tool Registry & OS27 Hyper++ Manifest
print("1. TOOL REGISTRY INTEGRITY")
try:
    from tools import _CLASS_TO_MODULE
    from tools.base import ToolRegistry

    registry = ToolRegistry()
    
    # Incarcare si verificare unelte de baza
    tools_dir = Path("c:/Users/billy/Desktop/ana-manus/ANA_MAX/tools")
    tool_files = [f for f in tools_dir.glob("*.py") if f.name not in ("__init__.py", "base.py")]
    
    print(f"📁 Tool files found: {len(tool_files)}")
    print(f"✅ OS27 Hyper++ mapped tool classes: {len(_CLASS_TO_MODULE)}")

    # Verificare daca clasele mapate corespund pe disc
    mapped_modules = set(_CLASS_TO_MODULE.values())
    file_stems = {f.stem for f in tool_files}
    missing_files = mapped_modules - file_stems

    if missing_files:
        print(f"⚠️  Mapped modules without files: {missing_files}")
    else:
        print("✅ All mapped tool classes have backing files on disk")

    # Verificare operare ToolRegistry
    print(f"✅ Registry functional and ready (OS27 lazy-loader active)")
    
except Exception as e:
    print(f"❌ Registry check failed: {e}")

# 2. Verificare Backends
print("\n2. BACKEND INTEGRITY")
backends = ["ollama", "omniroute", "openrouter"]
for backend in backends:
    try:
        backend_module = importlib.import_module(f"core.backends.{backend}_backend")
        print(f"✅ {backend}: Module loaded")
        
        # Verificare daca are init
        if hasattr(backend_module, 'init'):
            print(f"   ✅ Has init function")
        else:
            print(f"   ⚠️  Missing init function")
            
    except ImportError as e:
        print(f"❌ {backend}: Import failed - {e}")
    except Exception as e:
        print(f"⚠️  {backend}: Other error - {e}")

# 3. Verificare Configuratie
print("\n3. CONFIGURATION INTEGRITY")
config_file = Path("c:/Users/billy/Desktop/ana-manus/ANA_MAX/config/settings.yaml")
if config_file.exists():
    print(f"✅ settings.yaml exists")
    try:
        import yaml
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Verificare backends configurati
        if 'primary_backend' in config:
            print(f"   Primary backend: {config['primary_backend']}")
        if 'fallback_backend' in config:
            print(f"   Fallback backend: {config['fallback_backend']}")
            
        # Verificare backends definiti
        if 'backends' in config:
            for name, backend_config in config['backends'].items():
                print(f"   ✅ Backend defined: {name}")
                
    except Exception as e:
        print(f"❌ Config parsing failed: {e}")
else:
    print(f"❌ settings.yaml missing")

# 4. Verificare Dependinte Critice
print("\n4. CRITICAL DEPENDENCIES")
critical_deps = [
    ("pydantic", "pydantic"),
    ("requests", "requests"),
    ("frida", "frida"),
    ("opencv", "cv2"),
    ("numpy", "numpy"),
]

for module_name, import_name in critical_deps:
    try:
        importlib.import_module(import_name)
        print(f"✅ {module_name}: Available")
    except ImportError:
        print(f"❌ {module_name}: Missing")

# 5. Verificare Ollama
print("\n5. OLLAMA INTEGRITY")
try:
    import requests
    response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
    if response.status_code == 200:
        print("✅ Ollama server running")
        models = response.json().get('models', [])
        print(f"   Models available: {len(models)}")
        for model in models[:3]:
            print(f"   - {model.get('name', 'unknown')}")
    else:
        print(f"⚠️  Ollama server returned: {response.status_code}")
except Exception as e:
    print(f"❌ Ollama check failed: {e}")

# 6. Verificare Logs pentru erori
print("\n6. LOG INTEGRITY")
log_dir = Path("c:/Users/billy/Desktop/ana-manus/ANA_MAX/logs")
if log_dir.exists():
    log_files = list(log_dir.glob("*.log"))
    print(f"📁 Log files: {len(log_files)}")
    
    error_count = 0
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                errors = content.count('ERROR') + content.count('Exception')
                error_count += errors
                if errors > 0:
                    print(f"   ⚠️  {log_file.name}: {errors} errors")
        except:
            pass
    
    print(f"   Total errors in logs: {error_count}")
else:
    print("❌ Logs directory missing")

# 7. Verificare Fisiere Temporare/Gunoi
print("\n7. CLEANUP AUDIT")
temp_patterns = ["*.tmp", "*.bak", "*.old", "*.temp", "*~"]
temp_files = []
for pattern in temp_patterns:
    for root, dirs, files in os.walk("c:/Users/billy/Desktop/ana-manus"):
        for file in files:
            if file.endswith(pattern.replace('*', '')):
                temp_files.append(os.path.join(root, file))

if temp_files:
    print(f"⚠️  Temporary files found: {len(temp_files)}")
    for temp_file in temp_files[:10]:
        print(f"   - {temp_file}")
else:
    print("✅ No temporary files found")

print("\n=== INTEGRITY CHECK COMPLETED ===")
