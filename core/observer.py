"""
🧠 Ana Deep Learning Observer Module
Monitorizează activitatea utilizatorului și învață pattern-uri
"""

import os
import time
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import threading
from collections import defaultdict

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("⚠️ watchdog nu este instalat. Rulează: pip install watchdog --break-system-packages")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️ psutil nu este instalat. Rulează: pip install psutil --break-system-packages")


class LearningDatabase:
    """Baza de date pentru învățare și pattern-uri"""
    
    def __init__(self, db_path: str = "memory/learning.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Inițializează structura bazei de date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabel pentru evenimente fișiere
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event_type TEXT,
                file_path TEXT,
                file_extension TEXT,
                file_size INTEGER,
                hour_of_day INTEGER,
                day_of_week INTEGER
            )
        """)
        
        # Tabel pentru procese/aplicații
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS process_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                process_name TEXT,
                duration_seconds INTEGER,
                hour_of_day INTEGER,
                day_of_week INTEGER
            )
        """)
        
        # Tabel pentru comenzi executate
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                command TEXT,
                working_directory TEXT,
                success BOOLEAN,
                hour_of_day INTEGER
            )
        """)
        
        # Tabel pentru pattern-uri detectate
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT,
                pattern_data TEXT,
                confidence REAL,
                first_seen TEXT,
                last_seen TEXT,
                occurrence_count INTEGER
            )
        """)
        
        # Tabel pentru predicții și sugestii
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                prediction_type TEXT,
                prediction_data TEXT,
                confidence REAL,
                user_feedback TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_file_event(self, event_type: str, file_path: str):
        """Înregistrează un eveniment de fișier"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        file_ext = Path(file_path).suffix
        file_size = 0
        
        try:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
        except Exception:
            pass
        
        cursor.execute("""
            INSERT INTO file_events 
            (timestamp, event_type, file_path, file_extension, file_size, hour_of_day, day_of_week)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            now.isoformat(),
            event_type,
            file_path,
            file_ext,
            file_size,
            now.hour,
            now.weekday()
        ))
        
        conn.commit()
        conn.close()
    
    def log_process_event(self, process_name: str, duration: int):
        """Înregistrează un eveniment de proces"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        
        cursor.execute("""
            INSERT INTO process_events 
            (timestamp, process_name, duration_seconds, hour_of_day, day_of_week)
            VALUES (?, ?, ?, ?, ?)
        """, (
            now.isoformat(),
            process_name,
            duration,
            now.hour,
            now.weekday()
        ))
        
        conn.commit()
        conn.close()
    
    def log_command_event(self, command: str, working_dir: str, success: bool):
        """Înregistrează o comandă executată"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        
        cursor.execute("""
            INSERT INTO command_events 
            (timestamp, command, working_directory, success, hour_of_day)
            VALUES (?, ?, ?, ?, ?)
        """, (
            now.isoformat(),
            command,
            working_dir,
            success,
            now.hour
        ))
        
        conn.commit()
        conn.close()
    
    def get_file_patterns(self, days: int = 7) -> Dict[str, Any]:
        """Analizează pattern-uri de fișiere din ultimele N zile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Pattern-uri de extensii
        cursor.execute("""
            SELECT file_extension, COUNT(*) as count
            FROM file_events
            WHERE timestamp > datetime('now', '-' || ? || ' days')
            GROUP BY file_extension
            ORDER BY count DESC
            LIMIT 10
        """, (days,))
        
        extensions = dict(cursor.fetchall())
        
        # Pattern-uri de ore
        cursor.execute("""
            SELECT hour_of_day, COUNT(*) as count
            FROM file_events
            WHERE timestamp > datetime('now', '-' || ? || ' days')
            GROUP BY hour_of_day
            ORDER BY count DESC
        """, (days,))
        
        hours = dict(cursor.fetchall())
        
        # Pattern-uri de zile
        cursor.execute("""
            SELECT day_of_week, COUNT(*) as count
            FROM file_events
            WHERE timestamp > datetime('now', '-' || ? || ' days')
            GROUP BY day_of_week
            ORDER BY count DESC
        """, (days,))
        
        days_data = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "favorite_extensions": extensions,
            "active_hours": hours,
            "active_days": days_data
        }
    
    def get_process_patterns(self, days: int = 7) -> Dict[str, Any]:
        """Analizează pattern-uri de procese"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT process_name, COUNT(*) as count, SUM(duration_seconds) as total_time
            FROM process_events
            WHERE timestamp > datetime('now', '-' || ? || ' days')
            GROUP BY process_name
            ORDER BY total_time DESC
            LIMIT 10
        """, (days,))
        
        processes = {}
        for row in cursor.fetchall():
            processes[row[0]] = {
                "count": row[1],
                "total_time_seconds": row[2]
            }
        
        conn.close()
        return processes


class FileWatcher(FileSystemEventHandler):
    """Monitorizează modificările de fișiere"""
    
    def __init__(self, learning_db: LearningDatabase):
        self.learning_db = learning_db
        self.ignored_extensions = {'.tmp', '.log', '.swp', '.pyc', '__pycache__'}
        self.ignored_dirs = {'node_modules', '.git', '.venv', 'venv', '__pycache__'}
    
    def _should_ignore(self, path: str) -> bool:
        """Verifică dacă fișierul trebuie ignorat"""
        path_obj = Path(path)
        
        # Ignoră extensii temporare
        if path_obj.suffix in self.ignored_extensions:
            return True
        
        # Ignoră directoare specifice
        for part in path_obj.parts:
            if part in self.ignored_dirs:
                return True
        
        return False
    
    def on_created(self, event):
        if not event.is_directory and not self._should_ignore(event.src_path):
            print(f"📝 Fișier creat: {event.src_path}")
            self.learning_db.log_file_event("created", event.src_path)
    
    def on_modified(self, event):
        if not event.is_directory and not self._should_ignore(event.src_path):
            print(f"✏️ Fișier modificat: {event.src_path}")
            self.learning_db.log_file_event("modified", event.src_path)
    
    def on_deleted(self, event):
        if not event.is_directory and not self._should_ignore(event.src_path):
            print(f"🗑️ Fișier șters: {event.src_path}")
            self.learning_db.log_file_event("deleted", event.src_path)


class ProcessMonitor:
    """Monitorizează procesele active"""
    
    def __init__(self, learning_db: LearningDatabase):
        self.learning_db = learning_db
        self.tracked_processes = {}
        self.running = False
        self.monitor_thread = None
        
        # Procese de interes
        self.interesting_processes = {
            'code.exe': 'VS Code',
            'chrome.exe': 'Chrome',
            'firefox.exe': 'Firefox',
            'python.exe': 'Python',
            'node.exe': 'Node.js',
            'git.exe': 'Git',
            'cmd.exe': 'Command Prompt',
            'powershell.exe': 'PowerShell',
            'notepad++.exe': 'Notepad++',
            'sublime_text.exe': 'Sublime Text'
        }
    
    def start(self):
        """Pornește monitorizarea proceselor"""
        if not PSUTIL_AVAILABLE:
            print("⚠️ psutil nu este disponibil. Process monitoring dezactivat.")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("🔍 Process Monitor pornit")
    
    def stop(self):
        """Oprește monitorizarea"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
    
    def _monitor_loop(self):
        """Loop principal de monitorizare"""
        while self.running:
            try:
                current_processes = set()
                
                for proc in psutil.process_iter(['name', 'create_time']):
                    try:
                        proc_name = proc.info['name'].lower()
                        
                        if proc_name in self.interesting_processes:
                            pid = proc.pid
                            current_processes.add(pid)
                            
                            if pid not in self.tracked_processes:
                                # Proces nou detectat
                                self.tracked_processes[pid] = {
                                    'name': self.interesting_processes[proc_name],
                                    'start_time': time.time()
                                }
                                print(f"🚀 Aplicație pornită: {self.interesting_processes[proc_name]}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Detectează procese închise
                closed_pids = set(self.tracked_processes.keys()) - current_processes
                for pid in closed_pids:
                    proc_data = self.tracked_processes[pid]
                    duration = int(time.time() - proc_data['start_time'])
                    
                    if duration > 10:  # Ignoră procese foarte scurte
                        self.learning_db.log_process_event(proc_data['name'], duration)
                        print(f"⏹️ Aplicație închisă: {proc_data['name']} (durată: {duration}s)")
                    
                    del self.tracked_processes[pid]
                
            except Exception as e:
                print(f"⚠️ Eroare în process monitor: {e}")
            
            time.sleep(5)  # Check la fiecare 5 secunde


class PatternRecognizer:
    """Recunoaște pattern-uri din datele colectate"""
    
    def __init__(self, learning_db: LearningDatabase):
        self.learning_db = learning_db
    
    def analyze_work_patterns(self) -> Dict[str, Any]:
        """Analizează pattern-urile de lucru"""
        file_patterns = self.learning_db.get_file_patterns(days=7)
        process_patterns = self.learning_db.get_process_patterns(days=7)
        
        insights = {
            "timestamp": datetime.now().isoformat(),
            "file_insights": self._analyze_file_patterns(file_patterns),
            "process_insights": self._analyze_process_patterns(process_patterns),
            "recommendations": []
        }
        
        return insights
    
    def _analyze_file_patterns(self, patterns: Dict) -> Dict[str, Any]:
        """Analizează pattern-uri de fișiere"""
        insights = {}
        
        # Extensii favorite
        if patterns['favorite_extensions']:
            top_ext = list(patterns['favorite_extensions'].items())[0]
            insights['primary_language'] = self._extension_to_language(top_ext[0])
            insights['file_activity'] = patterns['favorite_extensions']
        
        # Ore active
        if patterns['active_hours']:
            peak_hour = max(patterns['active_hours'].items(), key=lambda x: x[1])[0]
            insights['peak_productivity_hour'] = peak_hour
        
        return insights
    
    def _analyze_process_patterns(self, patterns: Dict) -> Dict[str, Any]:
        """Analizează pattern-uri de procese"""
        insights = {}
        
        if patterns:
            # Aplicația cea mai folosită
            top_app = max(patterns.items(), key=lambda x: x[1]['total_time_seconds'])
            insights['most_used_app'] = {
                'name': top_app[0],
                'total_hours': round(top_app[1]['total_time_seconds'] / 3600, 2)
            }
        
        return insights
    
    def _extension_to_language(self, ext: str) -> str:
        """Mapează extensia la limbaj de programare"""
        mapping = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.html': 'HTML',
            '.css': 'CSS',
            '.md': 'Markdown'
        }
        return mapping.get(ext, ext)


class AnaObserver:
    """Clasa principală pentru modul Observer"""
    
    def __init__(self, watch_path: str = None):
        self.watch_path = watch_path or os.getcwd()
        self.learning_db = LearningDatabase()
        self.file_watcher = FileWatcher(self.learning_db)
        self.process_monitor = ProcessMonitor(self.learning_db)
        self.pattern_recognizer = PatternRecognizer(self.learning_db)
        self.observer = None
    
    def start(self):
        """Pornește toate sistemele de monitorizare"""
        print("🧠 Ana Deep Learning Observer se pornește...")
        print(f"📁 Monitorizez: {self.watch_path}")
        
        # Pornește file watcher
        if WATCHDOG_AVAILABLE:
            self.observer = Observer()
            self.observer.schedule(self.file_watcher, self.watch_path, recursive=True)
            self.observer.start()
            print("✅ File Watcher activ")
        else:
            print("⚠️ File Watcher dezactivat (watchdog lipsește)")
        
        # Pornește process monitor
        self.process_monitor.start()
        
        print("\n🎯 Ana observă și învață din activitatea ta!")
        print("💡 Apasă Ctrl+C pentru a opri\n")
    
    def stop(self):
        """Oprește toate sistemele"""
        print("\n🛑 Opresc Ana Observer...")
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.process_monitor.stop()
        print("✅ Ana Observer oprit")
    
    def get_insights(self) -> Dict[str, Any]:
        """Obține insights despre pattern-uri"""
        return self.pattern_recognizer.analyze_work_patterns()


if __name__ == "__main__":
    # Test standalone
    observer = AnaObserver()
    
    try:
        observer.start()
        
        # Rulează până la Ctrl+C
        while True:
            time.sleep(10)
            
            # Afișează insights la fiecare 60 secunde
            if int(time.time()) % 60 == 0:
                insights = observer.get_insights()
                print(f"\n📊 Insights: {json.dumps(insights, indent=2)}\n")
    
    except KeyboardInterrupt:
        observer.stop()
