import atexit
import subprocess

noisy = ['atom', 'chrome', 'firefox', 'dropbox']

def silence():
    subprocess.call(['pkill', '--signal', 'STOP', '|'.join(noisy)])
    def noise():
        subprocess.call(['pkill', '--signal', 'CONT', '|'.join(noisy)])
    atexit.register(noise)
