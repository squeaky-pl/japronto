from collections import namedtuple
import glob
import os.path

import pytoml
import pytest


testcase_fields = 'data,method,path,version,headers,body,error,disconnect'

HttpTestCase = namedtuple('HTTPTestCase', testcase_fields)


def parse_casesel(suite, casesel):
    for casespec in casesel.split('+'):
        *transforms, case = casespec.split(':')
        if case.endswith('!'):
            transforms.append('!')
            case = case[:-1]
        case = suite[case]

        for transform in reversed(transforms):
            func, *args = transform.split()
            case = transorm_dict[func](case, *args)

        yield case


def parametrize_cases(suite, *args):
    suite = suites[suite]
    cases_list = [
        list(parse_casesel(suite, sel)) for sel in args]
    return pytest.mark.parametrize('cases', cases_list, ids=args)


def load_casefile(path):
    result = {}

    with open(path) as casefile:
        cases = pytoml.load(casefile)

    for case_name, case_data in cases.items():
        case_data['data'] = case_data['data'].encode('utf-8')
        case_data['body'] = case_data['body'].encode('utf-8') \
            if 'body' in case_data else None
        case_data['disconnect'] = False
        case = HttpTestCase._make(
            case_data.get(f) for f in testcase_fields.split(','))
        result[case_name] = case

    return result


def load_cases():
    cases = {}

    for filename in glob.glob('cases/*.toml'):
        suite_name, _ = os.path.splitext(os.path.basename(filename))
        cases[suite_name] = load_casefile(filename)

    return cases


def keep_alive(case):
    headers = case.headers.copy()
    headers['Connection'] = 'keep-alive'
#    if case.body is not None \
#       and headers.get('Transfer-Encoding', 'identity') == 'identity':
#        headers['Content-Length'] = str(len(case.body))

    return update_case(case, headers)

def close(case):
    headers = case.headers.copy()
    headers['Connection'] = 'close'

    return update_case(case, headers)


def should_keep_alive(case):
    return case.headers.get(
        'Connection',
        'close' if case.version == '1.0' else 'keep-alive') == 'keep-alive'


def set_error(case, error):
    return update_case(case, error=error)


def disconnect(case):
    return update_case(case, disconnect=True)


def update_case(case, headers=False, error=False, disconnect=None):
    data = False
    if headers:
        data = bytearray()
        status = case.method + ' ' + case.path + ' HTTP/' + case.version + '\r\n'
        data += status.encode('ascii')
        for name, value in headers.items():
            data += name.encode('ascii') + b': ' + value.encode('latin1') + b'\r\n'
        data += b'\r\n'
        if case.body:
            data += case.body

    headers = headers or case.headers
    data = data or case.data
    error = error or case.error
    disconnect = disconnect if disconnect is not None else case.disconnect

    return case._replace(
        headers=headers, error=error, disconnect=disconnect,
        data=bytes(data))


transorm_dict = {
    'keep': keep_alive,
    'close': close,
    'e': set_error,
    '!': disconnect
}


suites = load_cases()
globals().update(suites)
