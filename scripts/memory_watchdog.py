#!/usr/bin/env python3
"""Memory watchdog - restarts service if memory exceeds threshold."""
import subprocess
import time
import os

MAX_MEMORY_MB = 400  # Restart if exceeds 300MB
CHECK_INTERVAL = 300  # Check every 5 minutes

def get_executor_memory():
    """Get executor RSS memory in MB."""
    try:
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True
        )
        for line in result.stdout.split('\n'):
            if 'Matrix.driver.executor' in line and 'grep' not in line:
                parts = line.split()
                rss_kb = int(parts[5])
                return rss_kb / 1024
    except:
        pass
    return 0

def restart_service():
    """Restart the pixel-pulse-neo service."""
    print(f"[memory_watchdog] Restarting service...", flush=True)
    subprocess.run(["sudo", "systemctl", "restart", "pixel-pulse-neo.service"])
    time.sleep(30)
    subprocess.run(["sudo", "systemctl", "restart", "pixel-pulse-neo-api.service"])
    print(f"[memory_watchdog] Service restarted", flush=True)

if __name__ == "__main__":
    print(f"[memory_watchdog] Starting with threshold {MAX_MEMORY_MB}MB", flush=True)
    while True:
        mem_mb = get_executor_memory()
        print(f"[memory_watchdog] Current memory: {mem_mb:.1f}MB", flush=True)
        if mem_mb > MAX_MEMORY_MB:
            print(f"[memory_watchdog] Memory {mem_mb:.1f}MB exceeds {MAX_MEMORY_MB}MB", flush=True)
            restart_service()
        time.sleep(CHECK_INTERVAL)
