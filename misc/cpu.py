"""
CPU file
"""


# module imports
import subprocess


# cpu location
CPU_PREFIX = '/sys/devices/system/cpu/'


def save():
    """
    save function
    """
    results = {}
    cpu_number = 0

    while True:
        try:
            _file = open(
                CPU_PREFIX + 'cpu{}/cpufreq/scaling_governor'.format(cpu_number))
        except:
            break

        governor = _file.read().strip()
        results.setdefault(cpu_number, {})['governor'] = governor

        _file.close()

        try:
            _file = open(
                CPU_PREFIX + 'cpu{}/cpufreq/scaling_cur_freq'.format(cpu_number))
        except:
            break

        results[cpu_number]['freq'] = _file.read().strip()

        _file.close()

        cpu_number += 1

    return results


def change(governor, freq=None):
    """
    change function
    """
    cpu_number = 0

    while True:
        try:
            subprocess.check_output([
                "sudo", "bash", "-c",
                "echo {governor} > {CPU_PREFIX}cpu{cpu_number}/cpufreq/scaling_governor"
                .format(governor=governor,
                        CPU_PREFIX=CPU_PREFIX,
                        cpu_number=cpu_number)],
                                    stderr=subprocess.STDOUT)
        except:
            break

        if freq:
            subprocess.check_output([
                "sudo", "bash", "-c",
                "echo {freq} > {CPU_PREFIX}cpu{cpu_number}/cpufreq/scaling_setspeed"
                .format(freq=freq,
                        CPU_PREFIX=CPU_PREFIX,
                        cpu_number=cpu_number)],
                                    stderr=subprocess.STDOUT)

        cpu_number += 1


def available_freq():
    """
    function for checking available frequency
    """
    _file = open(CPU_PREFIX + 'cpu0/cpufreq/scaling_available_frequencies')

    freq = [int(_file) for _file in _file.read().strip().split()]

    _file.close()

    return freq


def min_freq():
    """
    function for returning minimum available frequency
    """
    return min(available_freq())


def max_freq():
    """
    function for returning maximum avaliable frequency
    """
    return max(available_freq())


def dump():
    """
    dump function
    """

    try:
        sensors = subprocess.check_output('sensors').decode('utf-8')

    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Couldn't read CPU temp")

    else:
        cores = []

        for line in sensors.splitlines():
            if line.startswith('Core '):
                core, rest = line.split(':')
                temp = rest.strip().split()[0]
                cores.append((core, temp))

        for core, temp in cores:
            print(core + ':', temp)

    cpu_number = 0

    while True:
        try:
            _file = open(
                CPU_PREFIX + 'cpu{}/cpufreq/scaling_governor'.format(cpu_number))
        except:
            break

        print('Core ' + str(cpu_number) + ':', _file.read().strip(), end=', ')

        _file.close()

        try:
            _file = open(
                CPU_PREFIX + 'cpu{}/cpufreq/scaling_cur_freq'.format(cpu_number))
        except:
            break

        freq = round(int(_file.read()) / 10 ** 6, 2)

        print(freq, 'GHz')

        cpu_number += 1
