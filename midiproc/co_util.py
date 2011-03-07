"""
some coroutine helpers and utilities

References:
[dabeaz]: http://www.dabeaz.com/coroutines/
"""

from __future__ import with_statement

def coroutine(func):
    """
    prime the coroutine. Based on [dabeaz].
    """
    def start(*args,**kwargs):
        cr = func(*args,**kwargs)
        if hasattr(cr, '__next__'):
            cr.__next__()
        else:
            cr.next()
        return cr
    return start


class NullSink(object):
    """
    An instance of NullSink evaluates as False but will
    also act as a coroutine sink (i.e. can send() to it).

    Intended usage is to provide a safe default target
    to keep the code free of checks for targets existing.
    However the checks can still be made if required to
    avoid unncessary calculations due to the __bool__/__nonzero__
    special methods.
    example:

    >>> @coroutine
    ... def my_filter(target=None):
    ...     if target is None:
    ...         target = NullSink()
    ...     while True:
    ...         data = (yield)
    ...         # do stuff
    ...         target.send(data)
    ...
    >>> z = my_filter()
    >>> z.send('stuff')
    >>> z.close()
    """

    def send(self, _):
        pass
    def close(self):
        pass
    def throw(self, exc_type, exc_val=None, tb=None):
        pass

    def __bool__(self):
        return False
    def __nonzero__(self):
        return False

@coroutine
def hex_print(target=None):
    "This can be either a sink or a transparent filter"
    while True:
        rx = (yield)
        if isinstance(rx, (str,bytes)):
            print(' '.join('%02X'%(ord(c)) for c in rx))
        else:
            print('%02X '%(rx))
        if target:
            target.send(rx)

def iter_source(source, target):
    for entry in source:
        target.send(entry)
    target.close()

@coroutine
def broadcast(targets):
    while True:
        rx = (yield)
        for t in targets:
            t.send(rx)

def net_source(addr, target):
    # basic UDP
    import socket
    try:
        s = net_source._socket
    except AttributeError:
        s = net_source._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr) # TODO: have a mapping addr -> socket
    while True:
        # XXX: what is the equivalent of having a loop
        # and break on recv() returning null for TCP?
        # do we simply lose anything over (buflen) bytes
        # on a UDP recv?
        rx = s.recv(8192)
        target.send(rx)

@coroutine
def net_sink(addr):
    import socket
    try:
        s = net_sink._socket
    except AttributeError:
        s = net_sink._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        data = (yield)
        s.sendto(data, addr)


def file_source(path, target):
    with open(path) as f:
        while True:
            try:
                c = f.read(1)
                if c == '':
                    break
                target.send(c)
            except IOError:
                break
    target.close()

@coroutine
def file_sink(path):
    with open(path, 'wb') as f:
        while True:
            c = (yield)
            f.write(c)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
