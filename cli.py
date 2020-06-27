import time
import threading
from itertools import cycle, islice

from cmd import Cmd

from mido import (
    Message,
    MidiFile,
    open_input,
    get_output_names
)


def play_notes(output, channel, notes):
    """Play notes indefinetly."""
    t = threading.currentThread()

    for note in cycle(notes):
        # Start note
        output.send(Message('note_on',
                            note=note.pitch,
                            velocity=note.velocity,
                            channel=channel))
        # Sleep thread for note duration
        time.sleep(note.end_time - note.start_time)
        # Release note
        output.send(Message('note_off',
                    note=note.pitch,
                    velocity=note.velocity,
                    channel=channel))
        if getattr(t, "stop", False):
            break


def return_on_failure():
    def decorate(f):
        def applicator(*args, **kwargs):
            try:
                f(*args,**kwargs)
            except:
                print('Error')
        return applicator
    return decorate


class Prompt(Cmd):
    prompt = 'mg> '
    intro = "Welcome! Type ? to list commands"

    def __init__(self,
            input_device, output_port, channel, generator,
            *args, **kwargs):
        self.primer_melody = [60]
        self.temperature = 1.0
        self.num_steps = 128
        self.input_device = input_device
        self.output_port = output_port
        self.output_thread = None
        self.channel = channel
        self.generator = generator
        super(Prompt, self).__init__(*args, **kwargs)

    def play(self, notes):
        '''Send the notes to the MIDI output device.
        '''
        # stop the previous thread if it exists
        if self.output_thread:
            self.output_thread.stop = True

        # Start new thread playing notes
        # TODO Use same thread every time
        self.output_thread = threading.Thread(
            target=play_notes,
            args=(self.output_port, self.channel, notes),
            daemon=True)
        self.output_thread.start()

    def generate_and_play(self):
        '''Generate a new sequence and play it 
        on the output MIDI device.
        '''
        print("Generating new sequence",
            f"Primer: {self.primer_melody}",
            f"Length: {self.num_steps}",
            f"Temperature: {self.temperature}", sep='\n')

        sequence = self.generator.generate_sequence(
            self.primer_melody, self.num_steps, self.temperature)
        self.notes = sequence.notes
        self.play(self.notes)

    def do_exit(self, inp):
        '''exit
        Exit the application.'''
        print("Exiting")
        return True

    def do_stop(self, inp):
        '''stop
        Stop playback.
        '''
        if self.output_thread:
            self.output_thread.stop = True

    def do_play(self, inp):
        '''play
        Restart playback.
        '''
        if self.output_thread:
            self.play(self.notes)

    def do_new(self, inp):
        '''new
        Generates a new sequence with the current settings.
        '''
        self.generate_and_play()

    def do_primer(self, inp):
        '''primer [notes]
        Change the primer melody.
        Example: primer 48 51 57 60
        '''
        try:
            primer_melody = [int(n) for n in inp.split(' ')]
        except Exception:
            print("Could not process command")
        else:
            print('Setting new primer melody:', primer_melody)
            self.primer_melody = primer_melody
            self.generate_and_play()

    def do_record(self, inp):
        '''record [length]
        Record a new primer melody from an external MIDI device.
        Example: record 16
        '''
        try:
            primer_length = int(inp)
        except Exception:
            print("Could not process command")
        else:
            with open_input(self.input_device) as input_port:
                print(f"Waiting for input ({primer_length} notes)")
                primer_melody = []
                for message in islice(input_port, 2*primer_length):
                    print(message)
                    if message.type == 'note_on':
                        primer_melody.append(message.note)
                    if message.type == 'control_change':
                        primer_melody.append(-2)

            self.primer_melody = primer_melody
            self.generate_and_play()

    def do_temperature(self, inp):
        '''temperature [t]
        Change the temperature (amount of randomness) for the
        sequence generation.
        Example: temperature 1.3
        '''
        try:
            self.temperature = float(inp)
        except Exception:
            print("Could not process command")
        else:
            print('Setting new temperature:', self.temperature)
            self.generate_and_play()

    def do_steps(self, inp):
        '''steps [length]
        Change the number of steps in the generated sequence.
        Example: steps 64
        '''
        try:
            self.num_steps = int(inp)
        except Exception:
            print("Could not process command")
        else:
            print('Setting new sequence length:', self.num_steps)
            self.generate_and_play()

    def default(self, inp):
        if inp[:1] == 'p':
            return self.do_primer(inp[2:])
        elif inp[:1] == 'n':
            return self.do_restart()
        elif inp[:1] == '|':
            return self.do_stop()
        elif inp[:1] == '>':
            return self.do_play()
        elif inp[:1] == 'r':
            return self.do_record(inp[2:])
        elif inp[:1] == 't':
            return self.do_temperature(inp[2:])
        elif inp[:1] == 's':
            return self.do_steps(inp[2:])
        elif inp == 'x':
            return self.do_exit(inp[2:])
        else:
            print("Could not process command")

    do_EOF = do_exit

