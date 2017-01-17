import psutil
import sys
import time
# import matplotlib.pyplot as plt
import os
import json
from functools import partial


def report(pid, samples):
    plt.figure(figsize=(25,10))

    x = [s['t'] for s in samples if s['type'] == 'proc']

    lines = [s for s in samples if s['type'] == 'event']

    minuss = min(s['uss'] for s in samples if s['type'] == 'proc')
    ussplot = plt.subplot(211)
    ussplot.set_title('uss')
    ussplot.plot(
        x, [s['uss'] for s in samples if s['type'] == 'proc'], '.')
    for l in lines:
#        ussplot.text(l['t'], minuss, l['event'], horizontalalignment='right',
#            rotation=-90, rotation_mode='anchor')
        ussplot.axvline(l['t'])

    connplot = plt.subplot(212)
    connplot.set_title('conn')
    connplot.plot(
        x, [s['conn'] for s in samples if s['type'] == 'proc'], '.')

    os.makedirs('.reports', exist_ok=True)
    path = '.reports/{}.png'.format(pid)
    plt.savefig(path)

    return path


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


    #path = report(pid, samples)
    #print('Report saved to:', path)


if __name__ == '__main__':
    main()
