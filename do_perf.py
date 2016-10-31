import subprocess
import os
import sys
import argparse
import atexit

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
    print('pid', os.getpid())

    def cont():
        subprocess.check_call(['pkill', '--signal', 'CONT', 'firefox'])

    atexit.register(cont)
    subprocess.check_call(['pkill', '--signal', 'STOP', 'firefox'])

    argparser = argparse.ArgumentParser(description='do_perf')
    argparser.add_argument(
        '-p', '--parsers', dest='parsers', default='cffi,cext')
    argparser.add_argument(
        '-b', '--benchmarks', dest='benchmarks', default='http10long,websites,websitesn')

    result = argparser.parse_args(sys.argv[1:])
    parsers = result.parsers.split(',')
    benchmarks = result.benchmarks.split(',')

    one_shot = [b for b in benchmarks if b in ['http10long', 'websites']]
    multi_shot = [b for b in benchmarks if b in ['websitesn']]

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

    for dataset in one_shot:
        for parser in parsers:
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

    if multi_shot:
        for parser in parsers:
            print('-- website parts {} --'.format(parser))
            subprocess.check_call([
                'python', '-m', 'perf', 'timeit', '-s', setup.format(parser, 'websites'), loop])
            print()
