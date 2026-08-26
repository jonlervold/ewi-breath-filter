# EWI Breath Filter

A small macOS utility that reads MIDI from an Akai EWI USB, forwards only breath-controller CC2 messages, and exposes that stream as a virtual MIDI source named **EWI Breath Only**.

Target: macOS 11 Big Sur (Intel or Apple Silicon). Use Python 3.11 or 3.12.

## 1. Create a virtualenv

```bash
cd "/path/to/Mac EWI Breath Filter"
python3 -m venv venv
source venv/bin/activate
```

Use a python.org **3.11 or 3.12** installer. On an Intel Mac, use the Intel 64-bit build. Avoid Python 3.13: `python-rtmidi` 1.5.8 has no 3.13 wheels, and a source build would need Xcode.

## 2. Install requirements

```bash
pip install -r requirements.txt
```

This installs `python-rtmidi`, `PySimpleGUI`, and `PyInstaller`. Prebuilt wheels are used, so Xcode is not required.

## 3. Run from source

```bash
python3 main.py
```

1. Confirm the input dropdown selected your EWI (the first device whose name contains `EWI`).
2. Click **Start**.
3. Status should show `Running`, and **Breath CC** should update when you blow into the EWI.

Logs are written to `~/Library/Logs/EWI Breath Filter.log`.

## 4. Build with PyInstaller

With the venv activated:

```bash
chmod +x build.sh
./build.sh
```

This creates:

```text
dist/EWI Breath Filter.app
```

## 5. Launch the `.app`

- Double-click `dist/EWI Breath Filter.app`, or
- If Gatekeeper blocks it: Right-click the app → **Open** → **Open**.

Keep the app running while Pro Tools is using **EWI Breath Only**. Stopping in the UI only disconnects the physical EWI; the virtual port stays available until you quit the app.

## 6. Pro Tools setup

Expected routing:

```text
MIDI keyboard
    ↓
Pro Tools
    ↓
Entonal
    ↓
SWAM

EWI USB
    ↓
EWI Breath Filter
    ↓
"EWI Breath Only"
    ↓
Pro Tools
    ↓
SWAM
```

In Pro Tools:

1. Launch **EWI Breath Filter** first so **EWI Breath Only** appears as a MIDI source.
2. Enable **EWI Breath Only** as a MIDI input on the SWAM track.
3. Do **not** also use the raw EWI USB input on that SWAM track (notes, pitch bend, and other CCs would still arrive).
4. In SWAM, map expression/breath to **CC2**.

Use **Force output channel** only if SWAM or the track expects breath on a specific MIDI channel (1–16). By default the incoming channel is preserved.
