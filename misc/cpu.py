import subprocess

cpuprefix = '/sys/devices/system/cpu/'


def save():
    results = {}
    i = 0
    while 1:
        try:
            f = open(
                cpuprefix + 'cpu{}/cpufreq/scaling_governor'.format(i))
        except:
            break

        governor = f.read().strip()
        results.setdefault(i, {})['governor'] = governor

        f.close()

        try:
            f = open(
                cpuprefix + 'cpu{}/cpufreq/scaling_cur_freq'.format(i))
        except:
            break

        results[i]['freq'] = f.read().strip()

        f.close()

        i += 1

    return results


def change(governor, freq=None):
    i = 0
    while 1:
        try:
            subprocess.check_output([
                "sudo", "bash", "-c",
                "echo {governor} > {cpuprefix}cpu{i}/cpufreq/scaling_governor"
                .format(governor=governor, cpuprefix=cpuprefix, i=i)],
                stderr=subprocess.STDOUT)
        except:
            break

        if freq:
            subprocess.check_output([
                "sudo", "bash", "-c",
                "echo {freq} > {cpuprefix}cpu{i}/cpufreq/scaling_setspeed"
                .format(freq=freq, cpuprefix=cpuprefix, i=i)],
                stderr=subprocess.STDOUT)

        i += 1


def available_freq():
    f = open(cpuprefix + 'cpu0/cpufreq/scaling_available_frequencies')
    freq = [int(f) for f in f.read().strip().split()]
    f.close()

    return freq


def min_freq():
    return min(available_freq())


def max_freq():
    return max(available_freq())


def dump():
    try:
        sensors = subprocess.check_output('sensors').decode('utf-8')
    except (FileNotFoundError, subprocess.CalledProcessError):
        print('Couldnt read CPU temp')
    else:
        cores = []
        for line in sensors.splitlines():
            if line.startswith('Core '):
                core, rest = line.split(':')
                temp = rest.strip().split()[0]
                cores.append((core, temp))
        for core, temp in cores:
            print(core + ':', temp)

    i = 0
    while 1:
        try:
            f = open(
                cpuprefix + 'cpu{}/cpufreq/scaling_governor'.format(i))
        except:
            break

        print('Core ' + str(i) + ':', f.read().strip(), end=', ')

        f.close()

        try:
            f = open(
                cpuprefix + 'cpu{}/cpufreq/scaling_cur_freq'.format(i))
        except:
            break

        freq = round(int(f.read()) / 10 ** 6, 2)

        print(freq, 'GHz')

        i += 1
