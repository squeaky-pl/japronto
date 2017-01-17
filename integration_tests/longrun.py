import subprocess
import sys
import signal
import atexit
import os

sys.path.insert(0, '.')

import integration_tests.common
import integration_tests.generators
import client


def setup():
    subprocess.check_call([
        sys.executable, 'build.py', '--dest', '.test/longrun',
        '--kit', 'platform'])

    server = integration_tests.common.start_server(
        'integration_tests/dump.py', path='.test/longrun', sanitize=False)

    os.makedirs('.collector', exist_ok=True)

    os.putenv('COLLECTOR_FILE', '.collector/{}.json'.format(server.pid))
    collector = subprocess.Popen([
        sys.executable, 'collector.py', str(server.pid)])
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
    conn = client.Connection('localhost:8080')
    integration_tests.generators.send_requests(conn, 50, body=True)

def main():
    setup()
    run()


if __name__ == '__main__':
    main()
