import ast
import os
import time
import argparse
from itertools import cycle, islice
import threading
from cmd import Cmd

from mido import Message, MidiFile, open_output, open_input

import magenta
from magenta.models.melody_rnn import melody_rnn_model
from magenta.models.melody_rnn import melody_rnn_sequence_generator
from magenta.models.shared import sequence_generator_bundle
from magenta.music.protobuf import generator_pb2
from magenta.music.protobuf import music_pb2
import tensorflow.compat.v1 as tf
# set tensorflow logger level
tf.get_logger().setLevel('ERROR')


def run_generator(generator, primer_melody=[60], num_steps=128,
        temperature=1.0, beam_size=1, branch_factor=1, steps_per_iteration=1):
    """Generates melodies and saves them as MIDI files.

    Uses the options specified by the flags defined in this module.

    Args:
        generator: The MelodyRnnSequenceGenerator to use for generation.
    """    
    qpm = magenta.music.DEFAULT_QUARTERS_PER_MINUTE
    
    primer_melody = magenta.music.Melody(primer_melody)
    primer_sequence = primer_melody.to_sequence(qpm=qpm)

    # Derive the total number of seconds to generate based on the QPM of the
    # priming sequence and the num_steps flag.
    seconds_per_step = 60.0 / qpm / generator.steps_per_quarter
    total_seconds = num_steps * seconds_per_step

    # Specify start/stop time for generation based on starting generation at the
    # end of the priming sequence and continuing until the sequence is num_steps
    # long.
    generator_options = generator_pb2.GeneratorOptions()

    input_sequence = primer_sequence
    # Set the start time to begin on the next step after the last note ends.
    if primer_sequence.notes:
        last_end_time = max(n.end_time for n in primer_sequence.notes)
    else:
        last_end_time = 0
    generate_section = generator_options.generate_sections.add(
        start_time=last_end_time + seconds_per_step,
        end_time=total_seconds)

    if generate_section.start_time >= generate_section.end_time:
        raise ValueError(
            'Priming sequence is longer than the total number of steps '
            'requested: Priming sequence length: %s, Generation length '
            'requested: %s',
            generate_section.start_time, total_seconds)
        

    generator_options.args['temperature'].float_value = temperature
    generator_options.args['beam_size'].int_value = beam_size
    generator_options.args['branch_factor'].int_value = branch_factor
    generator_options.args['steps_per_iteration'].int_value = steps_per_iteration
    tf.logging.debug('input_sequence: %s', input_sequence)
    tf.logging.debug('generator_options: %s', generator_options)

    # Make the generate request and return it
    generated_sequence = generator.generate(input_sequence, generator_options)

    return generated_sequence


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

class Prompt(Cmd):
    prompt = 'mg> '
    intro = "Welcome! Type ? to list commands"

    primer_melody = [60]
    temperature = 1.0
    num_steps = 128
    input_device = None
    output_port = None
    output_thread = None
    channel = None
    generator = None
    
    def generate_and_play(self):
        if self.output_thread:
            self.output_thread.stop = True

        print("Generating sequence")
        sequence = run_generator(
            self.generator, 
            primer_melody=self.primer_melody,
            num_steps=self.num_steps,
            temperature=self.temperature)
        notes = sequence.notes
        # Start new thread playing notes
        self.output_thread = threading.Thread(
            target=play_notes, 
            args=(self.output_port, self.channel, notes), 
            daemon=True)
        self.output_thread.start()

    def do_exit(self, inp):
        '''Exit the application.'''
        print("Exiting")
        return True
 
    def do_primer(self, inp):
        '''Change the primer melody.'''
        primer_melody = [int(n) for n in inp.split(' ')]
        print('Setting new primer melody:', primer_melody)
        self.primer_melody = primer_melody
        self.generate_and_play()

    def do_record(self, inp):
        '''Record a new primer melody from an external MIDI device.'''
        primer_length = int(inp)
        with open_input("Arturia KeyStep 32") as input_port:
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
        '''Change the temperature (amount of randomness) for the sequence generation.'''
        self.temperature = float(inp)
        print('Setting new temperature:', self.temperature)
        self.generate_and_play()

    def do_steps(self, inp):
        '''Change the number of steps in the generated sequence.'''
        self.num_steps = int(inp)
        print('Setting new sequence length:', self.num_steps)
        self.generate_and_play()
    
    def default(self, inp):
        if inp[:1] == 'p':
            return self.do_primer(inp[2:])
        elif inp[:1] == 'r':
            return self.do_record(inp[2:])
        elif inp[:1] == 't':
            return self.do_temperature(inp[2:])
        elif inp[:1] == 's':
            return self.do_steps(inp[2:])
        elif inp == 'x':
            return self.do_exit(inp[2:])

    do_EOF = do_exit


def play(input_device, output_device, channel, generator):
    # TODO Separate code for CLI and application logic
    with open_output(output_device) as output:
        prompt = Prompt()
        prompt.input_device = input_device
        prompt.output_port = output
        prompt.channel = channel
        prompt.generator = generator

        prompt.generate_and_play()
        prompt.cmdloop()            

        # Release all notes 
        for note in range(128):
            output.send(Message('note_off', 
                        note=note, channel=channel))            

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", '-i', required=False, 
                        type=str, help="MIDI device for input")
    parser.add_argument("--output", '-o', required=True, 
                        type=str, help="MIDI device for output")
    parser.add_argument("--channel", '-ch', required=False, default=0, 
                        type=int, help="MIDI channel")
    parser.add_argument("--model", '-m', required=False, 
                        default='models/basic_rnn.mag', 
                        type=str, help='Path to magenta model')

    args = parser.parse_args()
   
    assert 1 <= args.channel <= 16, "MIDI Channel outside range 1..16"
    output_channel = args.channel - 1

    bundle_file = os.path.expanduser(args.model)
    bundle = sequence_generator_bundle.read_bundle_file(bundle_file)

    config_id = bundle.generator_details.id
    config = melody_rnn_model.default_configs[config_id]

    generator = melody_rnn_sequence_generator.MelodyRnnSequenceGenerator(
        model=melody_rnn_model.MelodyRnnModel(config),
        details=config.details,
        steps_per_quarter=config.steps_per_quarter,
        checkpoint=None,
        bundle=bundle)

    play(input_device=args.input, output_device=args.output, 
         channel=output_channel, generator=generator)
    

if __name__ == "__main__":
    main()
