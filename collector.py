import psutil
import sys
import time
import os
import json
from functools import partial


def sample_process(pid):
    process = psutil.Process(pid)
    samples = []

    while 1:
        try:
            uss = process.memory_full_info().uss
            conn = len(process.connections())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break

        samples.append({
            't': time.monotonic(),
            'uss': uss, 'conn': conn, 'type': 'proc'})
        time.sleep(.5)

    return samples


def main():
    pid = int(sys.argv[1])

    samples = sample_process(pid)

    with open(os.environ['COLLECTOR_FILE'], 'a') as fp:
        for sample in samples:
            fp.write(json.dumps(sample) + '\n')

    print('Collector info written to', os.environ['COLLECTOR_FILE'])

if __name__ == '__main__':
    main()
