import sys
sys.path.append('c:/Users/billy/Desktop/ana-manus/ANA_MAX')
from tools.unlimited_ocr_tool import UnlimitedOCRTool

tool = UnlimitedOCRTool()
result = tool.execute(
    file_path='c:/Users/billy/Desktop/ana-manus/test_large.json',
    output_file='c:/Users/billy/Desktop/ana-manus/test_large_output.txt'
)
print(f"Status: {result.status}")
print(f"Message: {result.message}")
if result.data:
    print(f"Tokens: {result.data.get('tokens', 'N/A')}")
    print(f"Text length: {len(result.data.get('text', ''))} characters")
    print(f"First 200 chars: {result.data.get('text', '')[:200]}")
