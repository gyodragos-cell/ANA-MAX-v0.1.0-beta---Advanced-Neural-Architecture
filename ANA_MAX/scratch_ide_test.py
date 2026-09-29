import psutil
ide_procs = [p for p in psutil.process_iter(['name', 'pid']) if p.info['name'] in ['Code.exe', 'Cursor.exe']]
for p in ide_procs:
    try:
        files = p.open_files()
        print(f"{p.info['name']} (PID {p.info['pid']}) has {len(files)} open files.")
        for f in files:
            if f.path.endswith('.py') or f.path.endswith('.md'):
                print(' ', f.path)
    except Exception as e:
        print(f"{p.info['name']} (PID {p.info['pid']}) error: {e}")
