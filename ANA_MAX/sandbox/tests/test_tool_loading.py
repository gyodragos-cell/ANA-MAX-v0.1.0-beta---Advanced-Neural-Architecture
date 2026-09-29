import sys
sys.path.append('c:/Users/billy/Desktop/ana-manus/ANA_MAX')

print("=== TEST TOOL LOADING ===\n")

# Test 1: Import direct
print("1. Import direct tool:")
try:
    from tools.large_file_reader import LargeFileReaderTool
    print("✅ LargeFileReaderTool importat direct")
except Exception as e:
    print(f"❌ Import direct esuat: {e}")

# Test 2: Import prin __init__
print("\n2. Import prin __init__:")
try:
    from tools import LargeFileReaderTool
    print("✅ LargeFileReaderTool importat prin __init__")
except Exception as e:
    print(f"❌ Import prin __init__ esuat: {e}")

# Test 3: Verificare ToolRegistry
print("\n3. Verificare ToolRegistry:")
try:
    from tools.base import ToolRegistry
    registry = ToolRegistry()
    print(f"✅ ToolRegistry creat")
    print(f"   Tools registered: {len(registry.list_tools())}")
    
    # Test manual registration
    print("\n4. Test manual registration:")
    try:
        from tools.large_file_reader import LargeFileReaderTool
        tool = LargeFileReaderTool()
        registry.register(tool)
        print(f"✅ Manual registration successful")
        print(f"   Tools registered: {len(registry.list_tools())}")
    except Exception as e:
        print(f"❌ Manual registration esuat: {e}")
        
except Exception as e:
    print(f"❌ ToolRegistry esuat: {e}")

# Test 4: Verificare daca tool-urile au get_definition
print("\n5. Verificare get_definition:")
try:
    from tools.large_file_reader import LargeFileReaderTool
    tool = LargeFileReaderTool()
    definition = tool.get_definition()
    print(f"✅ get_definition works")
    print(f"   Tool name: {definition.name}")
except Exception as e:
    print(f"❌ get_definition esuat: {e}")
