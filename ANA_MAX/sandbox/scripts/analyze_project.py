import sys
sys.path.append('c:/Users/billy/Desktop/ana-manus/ANA_MAX')
from tools.large_file_reader import LargeFileReaderTool
import os
from pathlib import Path
from datetime import datetime, timedelta

print("=== ANALIZA COMPLETA PROIECT ANA-MANUS ===\n")

tool = LargeFileReaderTool()
workspace = "c:/Users/billy/Desktop/ana-manus"
ana_max = f"{workspace}/ANA_MAX"

# 1. Analiza configuratie
print("1. ANALIZA CONFIGURATIE")
config_files = [
    f"{ana_max}/config/settings.yaml",
    f"{workspace}/docs/ROADMAP.md",
    f"{workspace}/docs/ARCHITECTURE.md"
]

for config_file in config_files:
    if os.path.exists(config_file):
        try:
            result = tool.execute(file_path=config_file, chunk_size=50, max_chunks=1)
            if result.status.value == 'success':
                print(f"✅ {Path(config_file).name}")
                print(f"   Lines: {result.data.get('total_lines', 0)}")
            else:
                print(f"❌ {Path(config_file).name}: {result.message}")
        except Exception as e:
            print(f"❌ {Path(config_file).name}: {e}")
    else:
        print(f"⚠️  {Path(config_file).name}: Nu exista")

# 2. Analiza fisiere mari
print("\n2. FISIERE MARI (>100KB)")
large_files = []
for root, dirs, files in os.walk(workspace):
    for file in files:
        file_path = os.path.join(root, file)
        try:
            size = os.path.getsize(file_path)
            if size > 100 * 1024:  # > 100KB
                size_kb = size / 1024
                large_files.append((file_path, size_kb))
        except:
            pass

large_files.sort(key=lambda x: x[1], reverse=True)
for file_path, size_kb in large_files[:15]:
    rel_path = file_path.replace(workspace, "")
    print(f"📄 {rel_path}")
    print(f"   Dimensiune: {size_kb:.2f} KB")

# 3. Analiza fisiere vechi
print("\n3. FISIERE VECHI (>6 luni)")
six_months_ago = datetime.now() - timedelta(days=180)
old_files = []
for root, dirs, files in os.walk(workspace):
    for file in files:
        file_path = os.path.join(root, file)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if mtime < six_months_ago:
                old_files.append((file_path, mtime))
        except:
            pass

old_files.sort(key=lambda x: x[1])
for file_path, mtime in old_files[:10]:
    rel_path = file_path.replace(workspace, "")
    print(f"📄 {rel_path}")
    print(f"   Ultima modificare: {mtime.strftime('%Y-%m-%d')}")

# 4. Analiza TODO/FIXME in cod
print("\n4. TODO/FIXME IN COD")
todo_count = 0
for root, dirs, files in os.walk(f"{ana_max}/core"):
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            try:
                result = tool.execute(file_path=file_path, chunk_size=1000, max_chunks=1)
                if result.status.value == 'success':
                    text = result.data.get('chunks', [{}])[0].get('text', '')
                    todos = text.count('TODO') + text.count('FIXME') + text.count('XXX')
                    if todos > 0:
                        rel_path = file_path.replace(ana_max, "")
                        print(f"📝 {rel_path}: {todos} TODO/FIXME")
                        todo_count += todos
            except:
                pass
print(f"   Total TODO/FIXME: {todo_count}")

# 5. Analiza logs
print("\n5. ANALIZA LOGS")
log_dir = f"{ana_max}/logs"
if os.path.exists(log_dir):
    log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
    for log_file in log_files[:5]:
        log_path = os.path.join(log_dir, log_file)
        try:
            result = tool.execute(file_path=log_path, chunk_size=50, max_chunks=1)
            if result.status.value == 'success':
                text = result.data.get('chunks', [{}])[0].get('text', '')
                errors = text.count('ERROR') + text.count('Exception')
                print(f"📋 {log_file}: {errors} erori")
        except:
            pass

# 6. Analiza dependente grele
print("\n6. DEPENDENTE GRELE")
venv_dir = f"{workspace}/venv"
if os.path.exists(venv_dir):
    heavy_deps = ['torch', 'torchvision', 'torchaudio', 'frida', 'opencv']
    for dep in heavy_deps:
        dep_path = f"{venv_dir}/Lib/site-packages/{dep}"
        if os.path.exists(dep_path):
            size = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, fn in os.walk(dep_path) for f in fn)
            size_mb = size / (1024 * 1024)
            print(f"📦 {dep}: {size_mb:.2f} MB")

print("\n=== ANALIZA COMPLETA FINALIZATA ===")
