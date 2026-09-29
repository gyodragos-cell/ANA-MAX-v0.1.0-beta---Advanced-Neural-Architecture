import json
import hashlib
from pathlib import Path
from datetime import datetime

class SemanticMemory:
    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.index_file = memory_dir / "semantic_index.json"
        self.index = self._load_index()

    def _load_index(self):
        if self.index_file.exists():
            try:
                with open(self.index_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {"files": {}, "last_update": None}
        return {"files": {}, "last_update": None}

    def _save_index(self):
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.index["last_update"] = datetime.now().isoformat()
        with open(self.index_file, "w") as f:
            json.dump(self.index, f, indent=4)

    def _get_file_hash(self, file_path: Path):
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def index_directory(self, root_dir: Path):
        print(f"[Memory] Indexing directory: {root_dir}")
        for py_file in root_dir.rglob("*.py"):
            file_hash = self._get_file_hash(py_file)
            rel_path = str(py_file.relative_to(root_dir.parent))
            
            # Simple metadata extraction (could be expanded with LLM summaries)
            self.index["files"][rel_path] = {
                "hash": file_hash,
                "last_indexed": datetime.now().isoformat(),
                "size": py_file.stat().st_size
            }
        self._save_index()
        print(f"[Memory] Indexed {len(self.index['files'])} files.")

    def search(self, query: str):
        # Placeholder for vector search
        # For now, just return files that match the query in their path
        results = []
        for path in self.index["files"]:
            if query.lower() in path.lower():
                results.append(path)
        return results

if __name__ == "__main__":
    # Example usage
    base_path = Path(os.getcwd()).parent
    mem = SemanticMemory(base_path / "memory")
    mem.index_directory(base_path / "core")
    
    print("\n--- Search Test ---")
    print("Search for 'kernel':", mem.search("kernel"))
