#!/usr/bin/env python3
import sys
current = None
count = duration = members = 0
def emit():
    if current is not None:
        print(f"{current[0]},{current[1]},{count},{duration:.3f},{members}")
for line in sys.stdin:
    station, hour, n, d, m = line.rstrip("\n").split("\t")
    key = (station, hour)
    if current is not None and key != current:
        emit(); count = duration = members = 0
    current = key; count += int(n); duration += float(d); members += int(m)
emit()

