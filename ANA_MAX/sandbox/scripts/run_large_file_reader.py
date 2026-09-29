import os
import sys
import argparse
from pathlib import Path

# Fix path to import the tool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from large_file_reader import LargeFileReaderTool

def main():
    parser = argparse.ArgumentParser(description="Read large files in chunks")
    parser.add_argument("file", help="Path to the file to read")
    parser.add_argument("--lines", type=int, default=1000, help="Lines per chunk")
    parser.add_argument("--max", type=int, default=1, help="Max chunks to print")
    args = parser.parse_args()

    tool = LargeFileReaderTool()
    res = tool.execute(file_path=args.file, chunk_size=args.lines, max_chunks=args.max)
    
    if res.status == "success":
        data = res.data
        print(f"File: {data['file_path']} | Lines: {data['total_lines']}")
        for chunk in data['chunks']:
            print(f"--- Chunk {chunk['chunk_number']} (Lines {chunk['start_line']}-{chunk['end_line']}) ---")
            print(chunk['text'])
            print("-" * 50)
    else:
        print(f"Error: {res.error}")

if __name__ == "__main__":
    main()
