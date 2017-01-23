import socket


def prepare_sock(sock):
    sock.listen(100)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.setblocking(False)
