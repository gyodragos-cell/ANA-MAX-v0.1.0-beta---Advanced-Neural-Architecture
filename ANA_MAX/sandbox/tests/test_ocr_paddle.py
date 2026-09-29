import sys
sys.path.append('c:/Users/billy/Desktop/ana-manus/ANA_MAX')
from tools.ocr_tool import run

# Test OCR pe fisier text (va fi tratat ca imagine daca e convertit)
result = run({
    'action': 'file',
    'file_path': 'c:/Users/billy/Desktop/ana-manus/test_text.txt'
})
print(result)
