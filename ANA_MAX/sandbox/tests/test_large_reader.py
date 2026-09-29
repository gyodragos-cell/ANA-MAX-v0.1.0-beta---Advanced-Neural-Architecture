import sys
sys.path.append('c:/Users/billy/Desktop/ana-manus/ANA_MAX')
from tools.large_file_reader import LargeFileReaderTool

tool = LargeFileReaderTool()
result = tool.execute(
    file_path='c:/Users/billy/Desktop/ana-manus/test_large.json',
    chunk_size=1000,
    max_chunks=10,
    output_file='c:/Users/billy/Desktop/ana-manus/test_large_output.txt'
)
print(f"Status: {result.status}")
print(f"Message: {result.message}")
if result.data:
    print(f"Total lines: {result.data.get('total_lines', 'N/A')}")
    print(f"Chunks returned: {result.data.get('chunks_returned', 'N/A')}")
    print(f"Total chars: {result.data.get('total_chars_returned', 'N/A')}")
    print(f"First chunk preview: {result.data.get('chunks', [{}])[0].get('text', '')[:200]}")
