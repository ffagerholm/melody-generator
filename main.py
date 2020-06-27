import sys
import argparse

from mido import (
    Message, 
    open_output, 
    get_output_names
)
from cli import Prompt
from model import MelodyGenerator


def start_app(input_device, output_device, channel, generator):
    with open_output(output_device) as output:
        prompt = Prompt(input_device, output, channel, generator)
        prompt.generate_and_play()
        prompt.cmdloop()            

        # Release all notes before exit
        for note in range(128):
            output.send(Message('note_off', 
                        note=note, channel=channel))            

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--list", '-l', required=False, action='store_true',
                        help="List available midi devices.")
    parser.add_argument("--input", '-i', required=False,
                        type=str, help="MIDI device for input")
    parser.add_argument("--output", '-o', required=False, 
                        type=str, help="MIDI device for output")
    parser.add_argument("--channel", '-ch', required=False, default=0, 
                        type=int, help="MIDI channel")
    parser.add_argument("--model", '-m', required=False, 
                        default='models/basic_rnn.mag', 
                        type=str, help='Path to magenta model')

    args = parser.parse_args()

    if args.list:
        devices = get_output_names()
        for name in devices:
            print(f"  - {name}")
    else:
        assert 1 <= args.channel <= 16, "MIDI Channel outside range 1..16"
        output_channel = args.channel - 1

        generator = MelodyGenerator(bundle_path=args.model)
        start_app(input_device=args.input, output_device=args.output, 
                  channel=output_channel, generator=generator)
    

if __name__ == "__main__":
    main()
