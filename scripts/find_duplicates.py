import os
import hashlib

def get_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def find_duplicates(directory):
    hashes = {}
    duplicates = {}
    for root, _, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                file_hash = get_file_hash(filepath)
                if file_hash in hashes:
                    if file_hash not in duplicates:
                        duplicates[file_hash] = [hashes[file_hash]]
                    duplicates[file_hash].append(filepath)
                else:
                    hashes[file_hash] = filepath
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
    return duplicates

if __name__ == "__main__":
    dir_to_scan = "C:\\\\Users\\\\billy\\\\Desktop\\\\ana-manus"
    duplicates = find_duplicates(dir_to_scan)
    with open("duplicates_report.txt", "w") as f:
        if duplicates:
            f.write("Duplicate files found:\\n")
            for hash_val, files in duplicates.items():
                f.write(f"\\nHash: {hash_val}\\n")
                for file in files:
                    f.write(f"  {file}\\n")
        else:
            f.write("No duplicate files found.\\n")
