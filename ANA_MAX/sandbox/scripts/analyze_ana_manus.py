import sys
sys.path.append('c:/Users/billy/Desktop/ana-manus')
from large_file_reader import LargeFileReaderTool

tool = LargeFileReaderTool()

# Analizam structura ana-manus
print("=== ANALIZA ANA-MANUS ===\n")

# 1. Verificam fisierele de configurare
print("1. Fisiere de configurare:")
config_files = [
    'c:/Users/billy/Desktop/ana-manus/ANA_MAX/config/settings.yaml',
    'c:/Users/billy/Desktop/ana-manus/ANA_MAX/config/config.yaml'
]

for config_file in config_files:
    try:
        result = tool.execute(file_path=config_file, chunk_size=50, max_chunks=1)
        if result.status.value == 'success':
            print(f"✅ {config_file}")
            print(f"   Lines: {result.data.get('total_lines', 0)}")
            print(f"   Preview: {result.data.get('chunks', [{}])[0].get('text', '')[:200]}")
        else:
            print(f"❌ {config_file}: {result.message}")
    except Exception as e:
        print(f"❌ {config_file}: {e}")
    print()

# 2. Verificam logs pentru probleme
print("2. Fisiere log:")
import os
log_dir = 'c:/Users/billy/Desktop/ana-manus/ANA_MAX/logs'
if os.path.exists(log_dir):
    log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
    for log_file in log_files[:5]:  # Primele 5 logs
        log_path = os.path.join(log_dir, log_file)
        try:
            result = tool.execute(file_path=log_path, chunk_size=50, max_chunks=1)
            if result.status.value == 'success':
                print(f"✅ {log_file}")
                print(f"   Lines: {result.data.get('total_lines', 0)}")
                # Cautam erori
                text = result.data.get('chunks', [{}])[0].get('text', '')
                errors = text.count('ERROR') + text.count('Exception') + text.count('Failed')
                print(f"   Erori detectate: {errors}")
            else:
                print(f"❌ {log_file}: {result.message}")
        except Exception as e:
            print(f"❌ {log_file}: {e}")
else:
    print("❌ Director logs nu exista")
print()

# 3. Verificam fisierele mari
print("3. Fisiere mari (>1MB):")
import os
total_size = 0
large_files = []
for root, dirs, files in os.walk('c:/Users/billy/Desktop/ana-manus'):
    for file in files:
        file_path = os.path.join(root, file)
        try:
            size = os.path.getsize(file_path)
            if size > 1024 * 1024:  # > 1MB
                size_mb = size / (1024 * 1024)
                large_files.append((file_path, size_mb))
                total_size += size
        except:
            pass

large_files.sort(key=lambda x: x[1], reverse=True)
for file_path, size_mb in large_files[:10]:
    print(f"📄 {file_path}")
    print(f"   Dimensiune: {size_mb:.2f} MB")

print(f"\nTotal spatiu ocupat de fisiere mari: {total_size / (1024*1024):.2f} MB")
