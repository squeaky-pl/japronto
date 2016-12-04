import asyncio


class Route:
    def __init__(self, pattern, handler, methods):
        self.pattern = pattern
        self.handler = handler
        self.methods = methods
        self.segments = parse(pattern)

    def __repr__(self):
        return '<Route {}, {} {}>'.format(self.pattern, self.methods, hex(id(self)))

    def describe(self):
        return self.pattern + (' ' if self.methods else '') + ' '.join(self.methods)

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
            raise ValueError('"}" must be followed by "/" or appear at the end')
        if name in names:
            raise ValueError('Duplicate name "{}" in pattern'.format(name))
        names.add(name)
        result.append(('placeholder', name))

    return result


from struct import Struct
from enum import IntEnum

class SegmentType(IntEnum):
    EXACT = 0
    PLACEHOLDER = 1

"""
typedef struct {
  PyObject* route;
  PyObject* handler;
  bool coro_func;
  size_t pattern_len;
  size_t methods_len;
  char buffer[];
} MatcherEntry;
"""
MatcherEntry = Struct('PP?NN')

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
ExactSegement = Struct('iN')
PlaceholderSegent = Struct('iN')
Segment = Struct('iN')


def compile(route):
    pattern_buf = b''
    for segment in route.segments:
        typ = getattr(SegmentType, segment[0].upper())
        pattern_buf += Segment.pack(typ, len(segment[1])) \
            + segment[1].encode('utf-8')
    methods_buf = ' '.join(route.methods).encode('ascii')
    methods_len = len(methods_buf)
    if methods_buf:
        methods_buf += b' '
        methods_len += 1

    return MatcherEntry.pack(
        id(route), id(route.handler),
        asyncio.iscoroutinefunction(route.handler),
        len(pattern_buf), methods_len) \
        + pattern_buf + methods_buf


def compile_all(routes):
    return b''.join(compile(r) for r in routes)
