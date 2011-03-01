"""
midiproc - a coroutine-based MIDI processing package
"""

from co_util import coroutine, net_source, hex_print, iter_source, net_sink, NullSink

EOX = '\xF7'  # end of sysex
SOX = '\xF0'  # start of sysex
SYS_COM_BASE = '\xF0'
SYS_RT_BASE = '\xF8'


@coroutine
def apply_tx_running_status(target):
    rstat = 0
    insysex = False
    data = (yield)
    if not insysex:
        rx = data[0]
        if rx == EOX: insysex = False
        elif rx == SOX: insysex = True
        elif rx >= SYS_COM_BASE:
            # system common - clear running status
            rstat = 0
        elif rx >= '\x80':
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
    updated = False
    running = True
    while True:
        rx = (yield) # get a byte (in str format)
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
        elif rx >= '\x80':
           rstat = rx
           bytecount = 2
           if '\xC0' <= rx <= '\xDF':
              bytecount = 1
           origbytecount = bytecount
           msg = rstat
        else: # databyte
            if rstat:
                msg += rx
                bytecount -= 1
                if bytecount == 0:
                    bytecount = origbytecount # reset counter for new databytes with rstat
                    msgbytes = map(ord, msg)
                    msg_target.send(msg)
                    msg = rstat
            # otherwise no running status - ignore databyte


@coroutine
def midi_out_ftdi():
    from pylibftdi import Device
    with Device() as d:
        d.baudrate = 31250
        while True:
            rx = (yield)
            d.write(rx)

@coroutine
def midi_in_ftdi(target):
    from pylibftdi import Device
    with Device() as d:
        d.baudrate = 31250
        while True:
            rx = d.read(1)
            target.send(rx)

@coroutine
def process_smf_track(target):
    import time
    # in: bytes from smf track
    # out: messages
    while True:
        l = 0
        for count in range(4):
            z = (yield)
            z = ord(z)
            l = l*128 + (z & 127)
            if (z & 128) == 0:
                break
        time.sleep(0.0005*l)

        rx = (yield)
        if (rx == SOX or rx == EOX):
            rx = (yield) # length
            length = ord(rx)
            for b in range(length):
                rx = (yield) # throw it away
            continue
        elif ( rx == '\xFF'): # meta event
            rx = (yield) # skip type - don't care
            rx = (yield) # length
            length = ord(rx)
            for b in range(length):
                rx = (yield)
            continue
        elif (rx >= '\x80'):
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
        if len(rx) == 3 and rx[0] == '\x80' or (rx[0] == '\x90' and rx[2] == '\x00'):
            continue
        target.send(rx)

@coroutine
def harmonize(target):
    while True:
        rx = (yield)
        if len(rx) == 3 and rx[0] == '\x90':
            target.send(rx)
            if rx[1] < '\x38':
                rx = ''.join((rx[0], chr(ord(rx[1]) - 24), rx[2]))
                target.send(rx)

from mid_data import d as midi_track
import itertools, functools

def main():
    chain = [functools.partial(iter_source,itertools.imap(chr, midi_track)),
             process_smf_track,
             midi_in_stream,
             hex_print,
             midi_out_ftdi]

    result = None
    for fn in reversed(chain):
        result = fn(result) if result is not None else fn()
#    iter_source(itertools.imap(chr,midi_track), 
#                process_smf_track(midi_in_stream(hex_print(midi_out_ftdi()))))

def net_client():
    chain = [functools.partial(iter_source,itertools.imap(chr, midi_track)),
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
             #drop_off,
             hex_print,
             #midi_out_ftdi
             ]

    result = None
    for fn in reversed(chain):
        result = fn(result) if result is not None else fn()


if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'client':
       net_client()
    elif sys.argv[1] == 'server':
       net_server()
