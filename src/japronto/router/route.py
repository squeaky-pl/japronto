import asyncio
from enum import IntEnum
from struct import Struct

from . import analyzer


class RouteNotFoundException(Exception):
    pass


class Route:
    def __init__(self, pattern, handler, methods):
        self.pattern = pattern
        self.handler = handler
        self.methods = methods
        self.segments = parse(pattern)
        self.placeholder_cnt = \
            sum(1 for s in self.segments if s[0] == 'placeholder')

    def __repr__(self):
        return '<Route {}, {} {}>'.format(
            self.pattern, self.methods, hex(id(self)))

    def describe(self):
        return self.pattern + (' ' if self.methods else '') + \
            ' '.join(self.methods)

    def __eq__(self, other):
        return self.pattern == other.pattern and self.methods == other.methods


def parse(pattern):
    names = set()
    result = []

    rest = pattern
    while rest:
        exact = ''
        while rest:
            chunk, _, rest = rest.partition('{')
            exact += chunk
            if rest and rest[0] == '{':
                exact += '{{'
                rest = rest[1:]
            else:
                break

        if exact:
            exact = exact.replace('{{', '{').replace('}}', '}')
            result.append(('exact', exact))
        if not rest:
            break

        name, _, rest = rest.partition('}')
        if not _:
            raise ValueError('Unbalanced "{" in pattern')
        if rest and rest[0] != '/':
            raise ValueError(
                '"}" must be followed by "/" or appear at the end')
        if name in names:
            raise ValueError('Duplicate name "{}" in pattern'.format(name))
        names.add(name)
        result.append(('placeholder', name))

    return result


class SegmentType(IntEnum):
    EXACT = 0
    PLACEHOLDER = 1


"""
typedef struct {
  PyObject* route;
  PyObject* handler;
  bool coro_func;
  bool simple;
  size_t pattern_len;
  size_t methods_len;
  size_t placeholder_cnt;
  char buffer[];
} MatcherEntry;
"""
MatcherEntry = Struct('PP??NNN')

"""
typedef enum {
  SEGMENT_EXACT,
  SEGMENT_PLACEHOLDER
} SegmentType;


typedef struct {
  size_t data_length;
  char data[];
} ExactSegment;


typedef struct {
  size_t name_length;
  char name[];
} PlaceholderSegment;


typedef struct {
  SegmentType type;

  union {
    ExactSegment exact;
    PlaceholderSegment placeholder;
  };
} Segment;
"""
ExactSegment = Struct('iN')
PlaceholderSegment = Struct('iN')
Segment = Struct('iN')


def roundto8(v):
    return (v + 7) & ~7


def padto8(data):
    """Pads data to the multiplies of 8 bytes.

       This makes x86_64 faster and prevents
       undefined behavior on other platforms"""
    length = len(data)
    return data + b'\xdb' * (roundto8(length) - length)


retain_handlers = set()


def compile(route):
    pattern_buf = b''
    for segment in route.segments:
        typ = getattr(SegmentType, segment[0].upper())
        pattern_buf += Segment.pack(typ, len(segment[1].encode('utf-8'))) \
            + padto8(segment[1].encode('utf-8'))
    methods_buf = ' '.join(route.methods).encode('ascii')
    methods_len = len(methods_buf)
    if methods_buf:
        methods_buf += b' '
        methods_len += 1
    methods_buf = padto8(methods_buf)

    handler = route.handler
    if asyncio.iscoroutinefunction(handler) \
       and analyzer.is_pointless_coroutine(handler):
        handler = analyzer.coroutine_to_func(handler)
        # since we save id to handler in matcher entry and this is the only
        # reference before INCREF-ed in matcher we store it in set to prevent
        # destruction
        retain_handlers.add(handler)

    return MatcherEntry.pack(
        id(route), id(handler),
        asyncio.iscoroutinefunction(handler),
        analyzer.is_simple(handler),
        len(pattern_buf), methods_len, route.placeholder_cnt) \
        + pattern_buf + methods_buf


def compile_all(routes):
    return b''.join(compile(r) for r in routes)
