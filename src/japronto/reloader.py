import sys
import subprocess
import signal

def main():
    process = subprocess.Popen([
        sys.executable, '-m', 'japronto',
        *(v for v in sys.argv[1:] if v != '--reload')])

    signal.signal(signal.SIGINT, lambda s, f: process.terminate())
    signal.signal(signal.SIGTERM, lambda s, f: process.terminate())

    process.wait()


if __name__ == "__main__":
    main()
