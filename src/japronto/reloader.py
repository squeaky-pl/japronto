import sys
import os.path
import time
import threading
import signal


def main():
    import subprocess

    terminating = False

    def terminate(*args):
        nonlocal terminating
        terminating = True
        child.terminate()

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)

    while not terminating:
        child = subprocess.Popen([
            sys.executable, '-m', 'japronto',
            *(v for v in sys.argv[1:] if v != '--reload')])

        child.wait()


def change_detector():
    previous_mtimes = {}

    while 1:
        changed = False
        current_mtimes = {}

        for name, module in sys.modules.items():
            try:
                filename = module.__file__
            except AttributeError:
                continue

            if not filename.endswith('.py'):
                continue

            mtime = os.path.getmtime(filename)
            previous_mtime = previous_mtimes.get(name)
            if previous_mtime and previous_mtime != mtime:
                changed = True

            current_mtimes[name] = mtime

        yield changed

        previous_mtimes = current_mtimes


class ChangeDetector(threading.Thread):
    def __init__(self, loop):
        super().__init__(daemon=True)
        self.loop = loop

    def run(self):
        for changed in change_detector():
            if changed:
                self.loop.call_soon_threadsafe(self.loop.stop)
                os.kill(os.getppid(), signal.SIGHUP)
                return
            time.sleep(.5)


if __name__ == "__main__":
    main()
