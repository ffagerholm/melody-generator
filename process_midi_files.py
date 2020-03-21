import os
from mido import Message, MidiFile, MidiTrack


def process(file_name, time_delta=63):
    mid_in = MidiFile(file_name)

    mid_out = MidiFile()

    on_count = 0

    for i, track in enumerate(mid_in.tracks):
        print('Track {}: {}'.format(i, track.name))
        track_out = MidiTrack()
        
        for msg in track:
            if msg.is_meta:
                track_out.append(msg)

            if msg.type == 'note_on':
                if 2 <= on_count <= 9:
                    print(on_count, msg)
                    track_out.append(Message('note_on', note=msg.note, velocity=100, time=0))
                    track_out.append(Message('note_off', note=msg.note, velocity=100, time=time_delta))
                on_count += 1

        mid_out.tracks.append(track_out)

    directory, fn = os.path.split(file_name)
    name, _ = fn.split('.')
    output_name = f"Output/{name} Processed.mid"
    mid_out.save(output_name)


def main():
    directory = "MIDI scales"
    (_, _, filenames) = next(os.walk(directory))

    for fn in filenames:
        file_name = os.path.join(directory, fn)
        print('Processing:', file_name)
        process(file_name)

    print('Done.')


if __name__ == "__main__":
    main()