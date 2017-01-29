import string
import re

from hypothesis import strategies as st
from hypothesis.strategies import \
    builds, integers, sampled_from, fixed_dictionaries, lists


_method_alphabet = ''.join(chr(x) for x in range(33, 256) if x != 127)
method = st.text(_method_alphabet, min_size=1)


_path_alphabet = st.characters(
    blacklist_characters='?', blacklist_categories=['Cs'])
path = st.text(_path_alphabet).map(lambda x: '/' + x)

_param_alphabet = st.characters(
    blacklist_characters='/?', blacklist_categories=['Cs'])
param = st.text(_param_alphabet, min_size=1)

query_string = st.one_of(st.text(), st.none())

_name_alphabet = string.digits + string.ascii_letters + '!#$%&\'*+-.^_`|~'
_names = st.text(_name_alphabet, min_size=1).map(lambda x: 'X-' + x)
_value_alphabet = ''.join(chr(x) for x in range(ord(' '), 256) if x != 127)
_is_illegal_value = re.compile(r'\n(?![ \t])|\r(?![ \t\n])').search
_values = st.text(_value_alphabet, min_size=1) \
    .filter(lambda x: not _is_illegal_value(x)).map(lambda x: x.strip())
headers = st.lists(st.tuples(_names, _values), max_size=48)

identity_body = st.one_of(st.binary(), st.none())
chunked_body = st.lists(st.binary(min_size=24))
body = st.one_of(st.binary(), st.none(), chunked_body)
