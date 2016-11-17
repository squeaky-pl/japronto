from protocol.tracing import CTracingProtocol, CffiTracingProtocol

from parser import cffiparser
try:
    from parser import cparser
except ImportError:
    cparser = None


if cparser:
    def make_cext(protocol_factory=CTracingProtocol):
        protocol = protocol_factory()
        parser = cparser.HttpRequestParser(
            protocol.on_headers, protocol.on_body, protocol.on_error)

        return parser, protocol


def make_cffi(protocol_factory=CffiTracingProtocol):
    protocol = protocol_factory()
    parser = cffiparser.HttpRequestParser(
        protocol.on_headers, protocol.on_body, protocol.on_error)

    return parser, protocol
