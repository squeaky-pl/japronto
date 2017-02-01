import subprocess
import sys
import signal
import atexit
import os
import time

sys.path.insert(0, '.')

import integration_tests.common  # noqa
import integration_tests.generators  # noqa

from misc import client  # noqa


def setup():
    subprocess.check_call([
        sys.executable, 'build.py', '--dest', '.test/longrun',
        '--kit', 'platform', '--disable-response-cache'])

    os.putenv('MALLOC_TRIM_THRESHOLD_', '0')
    server = integration_tests.common.start_server(
        'integration_tests/dump.py', path='.test/longrun', sanitize=False)
    os.unsetenv('MALLOC_TRIM_THRESHOLD_')

    os.makedirs('.collector', exist_ok=True)

    os.putenv('COLLECTOR_FILE', '.collector/{}.json'.format(server.pid))
    collector = subprocess.Popen([
        sys.executable, 'misc/collector.py', str(server.pid)])
    os.unsetenv('COLLECTOR_FILE')

    def cleanup(*args):
        try:
            server.terminate()
            assert server.wait() == 0
        finally:
            atexit.unregister(cleanup)

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, cleanup)


def run():
    time.sleep(2)
    for reverse in [True, False]:
        for combination in integration_tests.generators.generate_combinations(
          reverse=reverse):
            conn = client.Connection('localhost:8080')
            time.sleep(2)
            integration_tests.generators.send_requests(
                conn, 200, **combination)
            time.sleep(2)
            conn.close()
    time.sleep(2)


def main():
    setup()
    run()


if __name__ == '__main__':
    main()
