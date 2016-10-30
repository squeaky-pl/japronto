import subprocess

import parsers
import parts
import cases


def get_http10long():
    return cases.base['10long'].data


def get_websites(size=2 ** 18):
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

    setup += """
import parts
p = parts.make_parts(data, parts.fancy_series(1450))
"""

    loop = """
for i in p:
    parser.feed(i)
parser.feed_disconnect()
"""

    for parser in ['cffi', 'cext']:
        print('-- website parts {} --'.format(parser))
        subprocess.check_call([
            'python', '-m', 'perf', 'timeit', '-s', setup.format(parser, 'websites'), loop])
        print()
