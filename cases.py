from collections import namedtuple
import glob
import os.path

import pytoml
import pytest


testcase_fields = 'data,method,path,version,headers,body'

HttpTestCase = namedtuple('HTTPTestCase', testcase_fields)


def parametrize_cases(suite, *args):
    suite = suites[suite]
    cases_list = [
        [suite[c] for c in sel.split('+')] for sel in args]
    return pytest.mark.parametrize('cases', cases_list)


def load_casefile(path):
    result = {}

    with open(path) as casefile:
        cases = pytoml.load(casefile)

    for case_name, case_data in cases.items():
        case_data['data'] = case_data['data'].encode('utf-8')
        case_data['body'] = case_data['body'].encode('utf-8') \
            if 'body' in case_data else None
        case = HttpTestCase._make(
            case_data[f] for f in testcase_fields.split(','))
        result[case_name] = case

    return result


def load_cases():
    cases = {}

    for filename in glob.glob('cases/*.toml'):
        suite_name, _ = os.path.splitext(os.path.basename(filename))
        cases[suite_name] = load_casefile(filename)

    return cases


suites = load_cases()
globals().update(suites)
