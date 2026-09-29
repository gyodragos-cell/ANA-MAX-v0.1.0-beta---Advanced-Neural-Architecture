import json
import time
import socket
import threading
import GPUtil

class GPUAgent:
    def __init__(self, interval=5, duration=60, host='localhost', port=5050):
        self.interval = interval
        self.duration = duration
        self.host = host
        self.port = port
        self.loads = []          # store load percentages for summary
        self._stop_event = threading.Event()
        self._thread = None

    def _get_gpu_data(self):
        """Return GPU name, load%, and memory used% for the first GPU."""
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                return None, None, None
            gpu = gpus[0]  # take first GPU
            name = gpu.name
            load = gpu.load * 100          # load as percentage
            mem_used = gpu.memoryUtil * 100 # memory used as percentage
            return name, load, mem_used
        except Exception as e:
            print(f"Error reading GPU metrics: {e}")
            return None, None, None

    def send_data(self, name, load, mem_used):
        """Send JSON data to socket server."""
        data = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "gpu_name": name,
            "load_percent": round(load, 1),
            "memory_percent": round(mem_used, 1)
        }
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)  # avoid hanging
                sock.connect((self.host, self.port))
                sock.sendall(json.dumps(data).encode('utf-8'))
        except Exception as e:
            print(f"Socket error: {e}")

    def _run(self):
        """Main monitoring loop."""
        start_time = time.time()
        while not self._stop_event.is_set() and (time.time() - start_time) < self.duration:
            name, load, mem = self._get_gpu_data()
            if name is not None:
                self.send_data(name, load, mem)
                self.loads.append(load)
            # Sleep in small increments to allow early stop
            for _ in range(self.interval):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def start(self):
        """Start monitoring in background thread."""
        if self._thread and self._thread.is_alive():
            print("Agent already running.")
            return
        self.loads = []
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"GPU monitoring started (duration: {self.duration}s, interval: {self.interval}s).")

    def stop(self):
        """Stop monitoring and wait for thread."""
        if not self._thread or not self._thread.is_alive():
            return
        self._stop_event.set()
        self._thread.join()
        print("Monitoring stopped.")

    def summary(self):
        """Return average GPU load."""
        if not self.loads:
            return "No data collected."
        avg_load = sum(self.loads) / len(self.loads)
        return f"Average GPU load: {avg_load:.1f}% over {len(self.loads)} samples"

if __name__ == "__main__":
    agent = GPUAgent()
    try:
        agent.start()
        # Let it run for full duration (or until Ctrl+C)
        time.sleep(agent.duration + 1)  # allow last sample
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        agent.stop()
        print(agent.summary())