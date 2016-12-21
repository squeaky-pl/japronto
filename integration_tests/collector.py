import psutil
import sys
import time
import matplotlib.pyplot as plt
import os


def report(pid, samples):
    ussplot = plt.subplot(211)
    ussplot.set_title('uss')
    ussplot.plot([s['uss'] for s in samples] , '.')

    connplot = plt.subplot(212)
    connplot.set_title('conn')
    connplot.plot([s['conn'] for s in samples] , '.')

    os.makedirs('.reports', exist_ok=True)
    path = '.reports/{}.png'.format(pid)
    plt.savefig(path)

    return path


def main():
    pid = int(sys.argv[1])
    process = psutil.Process(pid)

    samples = []
    while 1:
        try:
            uss = process.memory_full_info().uss
            conn = len(process.connections())
        except psutil.NoSuchProcess:
            break

        samples.append({
            "uss": uss, "conn": conn,})
        time.sleep(1)

    path = report(pid, samples)
    print('Report saved to:', path)


if __name__ == '__main__':
    main()
