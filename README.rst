midiproc
========

midiproc - a coroutine-based MIDI processing package

midiproc is a small library containing various pluggable functions for
manipulating MIDI streams, based on coroutines.

:Features:

 - Supports Python 2 and Python 3

Examples
~~~~~~~~

::

    >>> from midiproc import midi_in_snddev, midi_in_stream, hex_print, midi_out_snddev, chain
    >>>
    >>> chain([midi_in_snddev, midi_in_stream, hex_print, midi_out_snddev])

License
-------

Copyright (c) 2011-2013 Ben Bass <benbass@codedstructure.net>

midiproc is released under the MIT licence; see the file "LICENSE.txt"
for information.
