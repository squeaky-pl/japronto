import subprocess

cpuprefix = '/sys/devices/system/cpu/'

def dump():
    sensors = subprocess.check_output('sensors').decode('utf-8')
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
