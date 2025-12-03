#!/usr/bin/env python3
"""Memory profiler to identify leaks."""
import tracemalloc
import time
import os
import sys

# Add project to path
sys.path.insert(0, '/home/jsdorais/dev/PixelPulseNeo')

tracemalloc.start()

# Take initial snapshot
snapshot1 = tracemalloc.take_snapshot()
print("Initial snapshot taken", flush=True)

# Wait and take another
time.sleep(60)
snapshot2 = tracemalloc.take_snapshot()

# Compare
top_stats = snapshot2.compare_to(snapshot1, 'lineno')

print("\n=== Top 20 memory increases ===", flush=True)
for stat in top_stats[:20]:
    print(stat, flush=True)

print("\n=== Top 20 by traceback ===", flush=True)
top_stats = snapshot2.compare_to(snapshot1, 'traceback')
for stat in top_stats[:10]:
    print(f"\n{stat}", flush=True)
    for line in stat.traceback.format():
        print(f"  {line}", flush=True)
