import time
import random
from mido import Message, MidiFile, open_output
from itertools import cycle
import threading
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--midi", '-f', required=True, type=str, help="MIDI file containing notes")
    parser.add_argument("--device", '-d', required=True, type=str, help="MIDI device")
    parser.add_argument("--channel", '-c', required=True, type=int, help="MIDI channel")
    parser.add_argument("--time", '-t', required=False, default=0.3, type=float, help="Note length")
    args = parser.parse_args()

    notes = []

    mid = MidiFile(args.midi)
    for i, track in enumerate(mid.tracks):
        print('Track {}: {}'.format(i, track.name))
        
        for msg in track:
            if msg.type == 'note_on':
                notes.append(msg.note)

    play(args.device, args.channel, notes, args.time)


def play_notes(output, channel, notes, delay, velocity):
    """Play notes indefinetly."""   
    t = threading.currentThread()
    for note in cycle(notes):
        output.send(Message('note_on', note=note, velocity=velocity, channel=channel))
        time.sleep(delay)
        output.send(Message('note_off', note=note, velocity=velocity, channel=channel))
        if getattr(t, "stop", False):
            break


def play(device, channel, notes, delay, velocity=100):
    with open_output(device) as output:
        print("Enter 's' to shuffle notes")
        try:
            while True:
                thread = threading.Thread(
                    target=play_notes, 
                    args=(output, channel, notes, delay, velocity), 
                    daemon=True)
                thread.start()

                command = input('>>> ')
                thread.stop = True

                if len(command) == 0:
                    continue
                elif command == 's':
                    random.shuffle(notes)
                    print('Shuffled notes:', notes)
                elif command[0] == 'v':
                    velocity = int(command.split(' ')[-1])
                    assert 0 <= velocity <= 127, "Velocity has to be between 0 and 127"
                    print("Velocity changed to:", velocity)
                elif command[0] == 'd':
                    delay = float(command.split(' ')[-1])
                    print('Note length changed to:', delay)
                elif command == 'exit':
                    break


        except:
            for note in notes:
                output.send(Message('note_off', note=note, velocity=100, channel=channel))            


if __name__ == "__main__":
    main()