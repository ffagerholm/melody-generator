# Melody generator 

Generate melodies using a Magenta [Melody RNN](https://github.com/tensorflow/magenta/tree/master/magenta/models/melody_rnn) model, and control the parameters for the generation in real time from a command line interface.

Capabilities:
- Send MIDI notes to a device of choice. 
- Set a primer melody 
- Record MIDI notes from an external device


## Get started

Version: `Python 3.6.9`
This specific version is required due to tensorflow requirements.

Install requirements by running

```bash
pip install -r requirements.txt
```

If the install fails, try upgrading pip and run again.

The code uses [mido](https://mido.readthedocs.io/en/latest/) for handling MIDI, and [TensorFlow Magenta](https://magenta.tensorflow.org/) for the machine-learning models.

> **NOTE** A Magenta Melody RNN model is required to run the application. Pretrained models can be dowloaded from [here](https://github.com/magenta/magenta/tree/master/magenta/models/melody_rnn#pre-trained).  
The downloaded models should be placed in the `models` directory. This app uses the `basic_rnn` model by default and expects it to be found as `models/basic_rnn.mag`.

## Usage

To list available MIDI devices use (does not start the app)

```bash
python main.py --list
```

To start the application and launch the command line interface, use (for example)

```bash
python main.py -i "Arturia KeyStep 32" -o "Boutique" -ch 4 
```

The app takes as arguments
- Name of MIDI device used for recording notes (optional)
- Name of MIDI device used for playing the generated sequence (required)
- MIDI Channel for the output (between 1 and 16) (optional, default is 1)
- Path to the magenta model used for sequence generation (optional)

A generated melody should start playing immediately after the application is
initialized (may take a few seconds due to loading the model).

The command line interface contains a number of options
- `stop`: Stop the playback
- `play`: Restart the playback
- `new`: Generate a new sequence with the current settings
- `primer`: Set a new primer sequence
- `steps`: Set the number of steps in the sequence
- `temperature`: Set the randomness level for the sequence generator
- `record`: Record primer notes from the input MIDI device
- `exit`: Exit the application

### Examples

#### New
Generate a new sequence with the current settings

Input
```bash
mg> new
```
Output
```bash
Generating new sequence
Primer: [60]
Length 128
Temperature: 1.0
```

#### Primer
Set a new primer, and generate a new sequence.
The note numbers should be separated by a single space.

Input
```bash
mg> primer 48 51 57 60
```
Output
```bash
Setting new primer melody: [48, 51, 57, 60]
Generating new sequence
Primer: [48, 51, 57, 60]
Length 128
Temperature: 1.0
```

#### Temperature
Set the temperature, and generate a new sequence.
The note numbers should be separated by a single space.

Input
```bash
mg> temperature 0.9
```
Output
```bash
Setting new temperature: 0.9
Generating new sequence
Primer: [48, 51, 57, 60]
Length 128
Temperature: 0.9
```

#### Record
Record primer notes from the input MIDI device specified when starting the app, and generate a new sequence.

To record 4 notes, run
Input
```bash
mg> record 4
```

The redcorded notes are shown in the output.
```
Waiting for input (4 notes)
note_on channel=3 note=48 velocity=79 time=0
note_off channel=3 note=48 velocity=64 time=0
note_on channel=3 note=51 velocity=88 time=0
note_off channel=3 note=51 velocity=64 time=0
note_on channel=3 note=57 velocity=86 time=0
note_off channel=3 note=57 velocity=64 time=0
note_on channel=3 note=60 velocity=102 time=0
note_off channel=3 note=60 velocity=64 time=0
Generating new sequence
Primer: [48, 51, 57, 60]
Length 128
Temperature: 1.0
```