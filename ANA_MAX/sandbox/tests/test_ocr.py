import sys
sys.path.append('c:/Users/billy/Desktop/ana-manus/ANA_MAX')
from tools.ocr_tool import run

result = run({'action': 'check'})
print(result)
