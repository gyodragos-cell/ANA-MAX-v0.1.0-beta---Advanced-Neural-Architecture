import sys
sys.path.append('c:/Users/billy/Desktop/ana-manus/ANA_MAX')
from tools.unlimited_ocr_tool import UnlimitedOCRTool

tool = UnlimitedOCRTool()
result = tool.run({
    'file_path': 'c:/Users/billy/Desktop/ana-manus/test_text.txt',
    'output_file': 'c:/Users/billy/Desktop/ana-manus/test_output.txt'
})
print(result)
