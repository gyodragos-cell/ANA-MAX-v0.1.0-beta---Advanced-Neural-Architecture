import sys
sys.path.append('c:/Users/billy/Desktop/ana-manus/ANA_MAX')

print("=== SMOKE TEST Large File Reader ===\n")

# Test 1: Import din tools package
print("1. Import din tools package...")
try:
    from tools import LargeFileReaderTool
    print("✅ Import reusit")
except Exception as e:
    print(f"❌ Import esuat: {e}")
    sys.exit(1)

# Test 2: Initializare tool
print("\n2. Initializare tool...")
try:
    tool = LargeFileReaderTool()
    print("✅ Initializare reusita")
except Exception as e:
    print(f"❌ Initializare esuata: {e}")
    sys.exit(1)

# Test 3: Citire fisier mic
print("\n3. Citire fisier mic de test...")
try:
    result = tool.execute(
        file_path='c:/Users/billy/Desktop/ana-manus/test_large.json',
        chunk_size=100,
        max_chunks=2
    )
    if result.status.value == 'success':
        print(f"✅ Citire reusita")
        print(f"   Total lines: {result.data.get('total_lines', 0)}")
        print(f"   Chunks returned: {result.data.get('chunks_returned', 0)}")
    else:
        print(f"❌ Citire esuata: {result.message}")
except Exception as e:
    print(f"❌ Citire esuata: {e}")
    sys.exit(1)

print("\n=== SMOKE TEST COMPLETAT CU SUCCES ===")
