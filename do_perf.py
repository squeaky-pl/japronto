import subprocess

import parsers
import cases


def get_http10long():
    return cases.base['10long'].data


def get_websites(size=2 ** 19):
    data = b''
    while len(data) < size:
        for c in cases.websites.values():
            data += c.data

    return data


if __name__ == '__main__':
    setup = """
import parsers
import do_perf
parser, *_ = parsers.make_{}(lambda: parsers.silent_callback)
data = do_perf.get_{}()
"""

    loop = """
parser.feed(data)
parser.feed_disconnect()
"""

    for dataset in ['http10long', 'websites']:
        for parser in ['cffi', 'cext']:
            print('-- {} {} --'.format(dataset, parser))
            subprocess.check_call([
                'python', '-m', 'perf', 'timeit', '-s', setup.format(parser, dataset), loop])
            print()
