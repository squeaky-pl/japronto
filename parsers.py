import impl_cffi
try:
    import impl_cext
except ImportError:
    impl_cext = None


def silent_callback(*args):
    pass


if impl_cext:
    def make_cext(cb_factory):
        on_headers = cb_factory()
        on_error = cb_factory()
        on_body = cb_factory()
        parser_cext = \
            impl_cext.HttpRequestParser(on_headers, on_body, on_error)

        return parser_cext, on_headers, on_error, on_body


def make_cffi(cb_factory):
    on_headers = cb_factory()
    on_error = cb_factory()
    on_body = cb_factory()
    parser_cffi = impl_cffi.HttpRequestParser(on_headers, on_body, on_error)

    return parser_cffi, on_headers, on_error, on_body
