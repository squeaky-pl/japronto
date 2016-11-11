import atexit
import subprocess


def silence():
    subprocess.call(['pkill', '--signal', 'STOP', 'firefox'])
    def noise():
        subprocess.call(['pkill', '--signal', 'CONT', 'firefox'])
    atexit.register(noise)
