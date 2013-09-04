"""
midiproc - a coroutine-based MIDI processing package
"""

from co_util import coroutine, net_source, iter_source, net_sink, NullSink, file_source

EOX = b'\xF7'  # end of sysex
SOX = b'\xF0'  # start of sysex
SYS_COM_BASE = b'\xF0'
SYS_RT_BASE = b'\xF8'


if b'\x00'[0] == 0:
    # if bytestrings are already int-like, make ord an identity function
    # (this is effectively a Python3 check, but pretending it's a bit more
    # subtle than that)
    ord = lambda x: x


@coroutine
def hex_print(target=None):
    "This can be either a sink or a transparent filter"
    while True:
        rx = (yield)
        if isinstance(rx, (str, bytes)):
            print(' '.join('%02X' % (ord(c)) for c in rx))
        else:
            print('%02X ' % (rx))
        if target:
            target.send(rx)


@coroutine
def apply_tx_running_status(target):
    rstat = 0
    insysex = False
    data = (yield)
    if not insysex:
        rx = data[0]
        if rx == EOX:
            insysex = False
        elif rx == SOX:
            insysex = True
        elif rx >= SYS_COM_BASE:
            # system common - clear running status
            rstat = 0
        elif rx >= b'\x80':
            if rstat == rx:
                data = data[1:]
            else:
                rstat = rx
    for byte in data:
        target.send(data)


@coroutine
def midi_in_stream(msg_target, rt_target=None, sysex_target=None):
    rt_target = rt_target or NullSink()
    sysex_target = sysex_target or NullSink()
    rstat = 0
    origbytecount = 0
    bytecount = 0
    msg = ''
    insysex = False
    sysex_msg = []
    while True:
        rx = (yield)  # get a byte (in str format)
        if (insysex and rx != EOX):
            if sysex_target:
                sysex_msg.append(rx)
        elif rx >= SYS_RT_BASE:
            # sysex or system realtime - ignore
            if rt_target:
                # realtime messages are only the single byte
                rt_target.send(rx)
        elif rx == EOX:
            insysex = False
            if sysex_target:
                sysex_target.send(sysex_msg)
            sysex_msg = []
        elif rx == SOX:
            insysex = True
            sysex_msg = []
        elif rx >= SYS_COM_BASE:
            # system common - clear running status
            rstat = 0
        elif rx >= b'\x80':
            rstat = rx
            bytecount = 2
            if b'\xC0' <= rx <= b'\xDF':
                bytecount = 1
            origbytecount = bytecount
            msg = rstat
        else:  # databyte
            if rstat:
                msg += rx
                bytecount -= 1
                if bytecount == 0:
                    # reset counter for new databytes with rstat
                    bytecount = origbytecount
                    msg_target.send(msg)
                    msg = rstat
            # otherwise no running status - ignore databyte


def midi_ftdi_dev():
    from pylibftdi import Device
    d = Device()
    d.baudrate = 31250
    return d


def midi_snddev(dev_name=None):
    import glob
    if dev_name is None:
        for pattern in '/dev/midi*', '/dev/snd/midi*':
            candidates = glob.glob(pattern)
            for c in candidates:
                try:
                    return open(c, 'rb')
                except OSError:
                    pass
    assert dev_name is not None
    return open(dev_name, 'rb')


def midi_out_ftdi():
    midi_writer(midi_ftdi_dev())


def midi_in_ftdi(target):
    midi_reader(midi_ftdi_dev(), target)


def midi_in_snddev(target, dev_name=None):
    midi_reader(midi_snddev(dev_name), target)


def midi_out_snddev(dev_name=None):
    midi_writer(midi_snddev(dev_name))


@coroutine
def midi_reader(source, target):
    while True:
        rx = source.read(1)
        target.send(rx)


@coroutine
def midi_writer(target):
    while True:
        rx = (yield)
        target.write(rx)


@coroutine
def process_smf_track(target):
    """
    in: bytes from smf track
    out: messages
    """
    import time
    tempo_us_per_beat = 1000000 / (120 / 60.0)

    # MThd header
    expected_header = 'MThd'
    for i in range(4):
        rx = (yield)
        assert rx == expected_header[i]
    length = 0
    for i in range(4):
        rx = (yield)
        length = 256 * length + ord(rx)
    assert length == 6, 'expected header length of 6'
    mid_fmt = 0
    for i in range(2):
        rx = (yield)
        mid_fmt = 256 * mid_fmt + ord(rx)
    assert mid_fmt == 0, 'only midi format 0 files supported (%d)' % mid_fmt
    track_count = 0
    for i in range(2):
        rx = (yield)
        track_count = 256 * track_count + ord(rx)
    assert track_count == 1, 'wanted a single track...'
    ppqn = 0
    for i in range(2):
        rx = (yield)
        ppqn = 256 * ppqn + ord(rx)
    # MTrk header
    expected_header = 'MTrk'
    for i in range(4):
        rx = (yield)
        assert rx == expected_header[i]
    length = 0
    for i in range(4):
        rx = (yield)
        length = 256 * length + ord(rx)
    # the data...
    while True:
        l = 0
        for count in range(4):
            z = (yield)
            z = ord(z)
            l = l * 128 + (z & 127)
            if (z & 128) == 0:
                break
        time.sleep(l / float(ppqn) * tempo_us_per_beat * 1.0e-6)

        rx = (yield)
        if (rx == SOX or rx == EOX):
            rx = (yield)  # length
            length = ord(rx)
            for b in range(length):
                rx = (yield)  # throw it away
            continue
        elif (rx == b'\xFF'):  # meta event
            rx = (yield)  # event type
            if rx == b'\x51':
                rx = (yield)
                assert rx == b'\x03'  # data length
                # set tempo
                tempo = 0
                for i in range(3):
                    rx = (yield)
                    tempo = 256 * tempo + ord(rx)
                tempo_us_per_beat = tempo
            else:  # don't care about other meta events
                rx = (yield)  # length
                length = ord(rx)
                for b in range(length):
                    rx = (yield)
            continue
        elif (rx >= b'\x80'):
            # get new running status
            rstat = rx
            rx = (yield)
        elif (rstat is None):
            raise ValueError('invalid MIDI stream')
        target.send(rstat)
        data1 = rx
        target.send(data1)
        if not (rstat >= 0xC0 and rstat <= 0xDF):
            data2 = (yield)
            target.send(data2)


@coroutine
def drop_off(target):
    while True:
        rx = (yield)
        if len(rx) == 3 and rx[0] == b'\x80' or (rx[0] == b'\x90' and rx[2] == b'\x00'):
            continue
        target.send(rx)


@coroutine
def harmonize(target):
    while True:
        rx = (yield)
        if len(rx) == 3 and rx[0] == b'\x90':
            target.send(rx)
            if rx[1] < b'\x38':
                rx = ''.join((rx[0], chr(ord(rx[1]) - 24), rx[2]))
                target.send(rx)

from mid_data import d as midi_track
import itertools
import functools


def main():
    chain = [
        # functools.partial(iter_source,itertools.imap(chr, midi_track)),
        functools.partial(file_source, 'virus_arp.mid'),
        process_smf_track,
        midi_in_stream,
        hex_print,
        midi_out_ftdi
    ]

    chain = [midi_in_snddev, midi_in_stream, hex_print, midi_out_snddev]

    result = None
    for fn in reversed(chain):
        result = fn(result) if result is not None else fn()
#    iter_source(itertools.imap(chr,midi_track),
#                process_smf_track(midi_in_stream(hex_print(midi_out_ftdi()))))


def net_client():
    chain = [functools.partial(iter_source, itertools.imap(chr, midi_track)),
             process_smf_track,
             midi_in_stream,
             hex_print,
             functools.partial(net_sink, ('localhost', 4455))]

    result = None
    for fn in reversed(chain):
        result = fn(result) if result is not None else fn()


def net_server():
    chain = [functools.partial(net_source, ('localhost', 4455)),
             hex_print,
             harmonize,
             # drop_off,
             hex_print,
             # midi_out_ftdi
             ]

    result = None
    for fn in reversed(chain):
        result = fn(result) if result is not None else fn()


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        main()
    elif sys.argv[1] == 'client':
        net_client()
    elif sys.argv[1] == 'server':
        net_server()
