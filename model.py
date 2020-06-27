import os

import magenta
from magenta.models.melody_rnn import melody_rnn_model
from magenta.models.melody_rnn import melody_rnn_sequence_generator
from magenta.models.shared import sequence_generator_bundle
from magenta.music.protobuf import generator_pb2
from magenta.music.protobuf import music_pb2
import tensorflow.compat.v1 as tf
# set tensorflow logger level to avoid unnecessary output
tf.get_logger().setLevel('ERROR')


class MelodyGenerator():
    """RNN model for generating melodies based on a few notes."""
    def __init__(self, bundle_path: str):
        """Initialize model from bundle.

        bundle_path (str): Path to the MelodyRnnSequenceGenerator to use for generation.
        """
        bundle_file = os.path.expanduser(bundle_path)
        bundle = sequence_generator_bundle.read_bundle_file(bundle_file)

        config_id = bundle.generator_details.id
        config = melody_rnn_model.default_configs[config_id]

        self.generator = melody_rnn_sequence_generator.MelodyRnnSequenceGenerator(
            model=melody_rnn_model.MelodyRnnModel(config),
            details=config.details,
            steps_per_quarter=config.steps_per_quarter,
            checkpoint=None,
            bundle=bundle)


    def generate_sequence(self, primer_melody=[60], num_steps=128,
            temperature=1.0, beam_size=1, branch_factor=1, 
            steps_per_iteration=1):
        """Generates melodies and saves them as MIDI files.

        Uses the options specified by the flags defined in this module.

        Args:
            primer_melody (list): The startoff point for the sequence.
                Is always part of the returned sequence, ex. if the 
                primer_melody melody is [60, 61, 62] the generated 
                sequence start with notes [60, 61, 62, ...].
                Default is [60]

            num_steps (int): Number of steps in the generated sequence.
                Default is 128

            temperature (int): Controles the amount of randomness 
                in the sequence generation. Default is 1.0

            beam_size (int): Default is 1

            branch_factor (int): Default is 1

            steps_per_iteration (int): Default is 1
        """    
        qpm = magenta.music.DEFAULT_QUARTERS_PER_MINUTE
        
        primer_melody = magenta.music.Melody(primer_melody)
        primer_sequence = primer_melody.to_sequence(qpm=qpm)

        # Derive the total number of seconds to generate based on the QPM of the
        # priming sequence and the num_steps flag.
        seconds_per_step = 60.0 / qpm / self.generator.steps_per_quarter
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
        generated_sequence = self.generator.generate(input_sequence, generator_options)

        return generated_sequence
