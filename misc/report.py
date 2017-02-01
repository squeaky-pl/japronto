import matplotlib.pyplot as plt
import sys
import os
import json


def report(samples, pid):
    plt.figure(figsize=(25, 10))

    x = [s['t'] for s in samples if s['type'] == 'proc']

    lines = [s for s in samples if s['type'] == 'event']

    # minuss = min(s['uss'] for s in samples if s['type'] == 'proc')
    ussplot = plt.subplot(211)
    ussplot.set_title('uss')
    ussplot.plot(
        x, [s['uss'] for s in samples if s['type'] == 'proc'], '.')
    for l in lines:
        # ussplot.text(l['t'], minuss, l['event'], horizontalalignment='right',
        # rotation=-90, rotation_mode='anchor')
        ussplot.axvline(l['t'])

    connplot = plt.subplot(212)
    connplot.set_title('conn')
    connplot.plot(
        x, [s['conn'] for s in samples if s['type'] == 'proc'], '.')

    os.makedirs('.reports', exist_ok=True)
    path = '.reports/{}.png'.format(pid)
    plt.savefig(path)

    return path


def load(filepath):
    samples = []
    with open(filepath) as fp:
        for line in fp:
            line = line.strip()
            samples.append(json.loads(line))

    return samples


def order(samples):
    return sorted(samples, key=lambda x: x['t'])


def normalize_time(samples):
    if not samples:
        return []

    base_time = samples[0]['t']

    return [{**s, 't': s['t'] - base_time} for s in samples]


def main():
    samples = load(sys.argv[1])
    pid, _ = os.path.splitext(os.path.basename(sys.argv[1]))
    samples = order(samples)
    samples = normalize_time(samples)
    report(samples, pid)


if __name__ == '__main__':
    main()
