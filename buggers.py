import atexit
import psutil

noisy = ['atom', 'chrome', 'firefox', 'dropbox', 'opera', 'spotify']

def silence():
    for proc in psutil.process_iter():
        if proc.name() in noisy:
            proc.suspend()

    def noise():
        for proc in psutil.process_iter():
            if proc.name() in noisy:
                proc.resume()
    atexit.register(noise)
