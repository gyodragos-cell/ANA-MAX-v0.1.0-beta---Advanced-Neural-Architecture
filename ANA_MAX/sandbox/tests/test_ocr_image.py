import sys
sys.path.append('c:/Users/billy/Desktop/ana-manus/ANA_MAX')
from tools.ocr_tool import run

# Test OCR pe imagine existenta
result = run({
    'action': 'file',
    'image_path': 'c:/Users/billy/Desktop/ana-manus/ANA_MAX/screenshots/desktop_20260727_230127.png'
})
print(result)
