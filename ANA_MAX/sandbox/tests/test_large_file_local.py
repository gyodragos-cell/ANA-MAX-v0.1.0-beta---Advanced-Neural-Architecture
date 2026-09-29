#!/usr/bin/env python3
"""Test direct tool local large_file_reader"""

import sys
import os
import json

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ANA_MAX"))

from tools.large_file_reader import LargeFileReaderTool

def test_large_file():
    tool = LargeFileReaderTool()
    
    result = tool.execute(
        file_path=r"C:\Users\billy\Desktop\ana-manus\docs\ANA_MEMORY.md",
        chunk_size=100,
        max_chunks=10
    )
    
    print("STATUS:", result.status.value)
    print("MESSAGE:", result.message.encode('ascii', 'ignore').decode('ascii'))
    
    if result.status.value == "success":
        data = result.data
        print("\n--- CHUNK DATA ---")
        print(f"Total lines: {data['total_lines']}")
        print(f"Chunks returned: {data['chunks_returned']}")
        print(f"Chars returned: {data['total_chars_returned']}")
        
        if data['chunks']:
            chunk = data['chunks'][0]
            print(f"\nChunk {chunk['chunk_number']} (lines {chunk['start_line']}-{chunk['end_line']}):")
            # Print safely avoiding unicode issues
            text = chunk['text'].encode('ascii', 'ignore').decode('ascii')
            print(text[:500])

if __name__ == "__main__":
    test_large_file()
