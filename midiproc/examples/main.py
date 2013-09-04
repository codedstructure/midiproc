from midiproc import *
from midiproc.examples.mid_data import d as midi_track
import itertools
import functools


def main():
    """
    chain([
        # functools.partial(iter_source,itertools.imap(chr, midi_track)),
        functools.partial(file_source, 'virus_arp.mid'),
        process_smf_track,
        midi_in_stream,
        hex_print,
        midi_out_ftdi
    ])
    """

    chain([midi_in_snddev, midi_in_stream, hex_print, midi_out_snddev])


def net_client():
    chain([functools.partial(iter_source, itertools.imap(chr, midi_track)),
           process_smf_track,
           midi_in_stream,
           hex_print,
           functools.partial(net_sink, ('localhost', 4455))])


def net_server():
    chain([functools.partial(net_source, ('localhost', 4455)),
           hex_print,
           harmonize,
           # drop_off,
           hex_print,
           # midi_out_ftdi,
          ])


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        main()
    elif sys.argv[1] == 'client':
        net_client()
    elif sys.argv[1] == 'server':
        net_server()
