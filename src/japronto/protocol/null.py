class NullProtocol:
    def on_headers(self, *args):
        pass

    def on_body(self, body):
        pass

    def on_error(self, error):
        pass
