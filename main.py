#!/usr/bin/env python3
"""EWI Breath Filter: forward only breath CC2 from an EWI to a virtual MIDI source."""

import logging
import os
import sys

import PySimpleGUI as sg
import rtmidi

APP_NAME = "EWI Breath Filter"
CLIENT_NAME = "EWI Breath Filter"
VIRTUAL_PORT_NAME = "EWI Breath Only"
CC_BREATH = 2
STATUS_CC = 0xB0

LOG_DIR = os.path.join(os.path.expanduser("~"), "Library", "Logs")
LOG_PATH = os.path.join(LOG_DIR, "EWI Breath Filter.log")


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    handlers = [logging.StreamHandler(sys.stderr)]
    try:
        handlers.append(logging.FileHandler(LOG_PATH, encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


class BreathFilter:
    def __init__(self, window):
        self.window = window
        self.midi_in = None
        self.midi_out = None
        self.force_channel = False
        self.channel = 1
        self.running = False

    def list_inputs(self):
        probe = None
        try:
            probe = rtmidi.MidiIn(name=CLIENT_NAME)
            ports = list(probe.get_ports() or [])
        except Exception:
            logging.exception("Failed to list MIDI input devices")
            ports = []
        finally:
            if probe is not None:
                del probe
        return [name for name in ports if name and name != VIRTUAL_PORT_NAME]

    def default_input(self, ports):
        for name in ports:
            if "ewi" in name.lower():
                return name
        if ports:
            return ports[0]
        return None

    def ensure_virtual_out(self):
        if self.midi_out is not None and self.midi_out.is_port_open():
            return
        self.midi_out = rtmidi.MidiOut(name=CLIENT_NAME)
        self.midi_out.open_virtual_port(VIRTUAL_PORT_NAME)
        logging.info("Created virtual MIDI output: %s", VIRTUAL_PORT_NAME)

    def start(self, port_name):
        if self.running:
            return
        if not port_name:
            raise ValueError("No MIDI input device selected.")

        self.ensure_virtual_out()

        midi_in = rtmidi.MidiIn(name=CLIENT_NAME)
        ports = list(midi_in.get_ports() or [])
        logging.info("Detected MIDI devices: %s", ports)
        try:
            index = ports.index(port_name)
        except ValueError:
            del midi_in
            raise ValueError("MIDI input device not found: %s" % port_name)

        try:
            midi_in.ignore_types(sysex=True, timing=True, active_sensing=True)
            midi_in.open_port(index)
            midi_in.set_callback(self._callback)
        except Exception:
            try:
                midi_in.close_port()
            except Exception:
                pass
            del midi_in
            raise

        self.midi_in = midi_in
        self.running = True
        logging.info("Selected MIDI input: %s", port_name)
        logging.info("Started")

    def stop(self):
        midi_in = self.midi_in
        self.midi_in = None
        self.running = False
        if midi_in is None:
            return
        try:
            midi_in.cancel_callback()
        except Exception:
            logging.exception("Error canceling MIDI callback")
        try:
            if midi_in.is_port_open():
                midi_in.close_port()
        except Exception:
            logging.exception("Error closing MIDI input")
        del midi_in
        logging.info("Stopped")

    def close(self):
        self.stop()
        midi_out = self.midi_out
        self.midi_out = None
        if midi_out is None:
            return
        try:
            if midi_out.is_port_open():
                midi_out.close_port()
        except Exception:
            logging.exception("Error closing virtual MIDI output")
        del midi_out
        logging.info("Closed virtual MIDI output")

    def _callback(self, event, data=None):
        try:
            message, _dt = event
            if not (
                len(message) >= 3
                and (message[0] & 0xF0) == STATUS_CC
                and message[1] == CC_BREATH
            ):
                return
            out = list(message)
            if self.force_channel:
                out[0] = STATUS_CC | (self.channel - 1)
            if self.midi_out is not None:
                self.midi_out.send_message(out)
            logging.debug("CC2 value=%s", out[2])
            self.window.write_event_value("-BREATH-", out[2])
        except Exception as exc:
            logging.exception("MIDI callback error")
            try:
                self.window.write_event_value("-ERROR-", str(exc))
            except Exception:
                pass


def refresh_devices(window, filt):
    ports = filt.list_inputs()
    logging.info("Detected MIDI devices: %s", ports)
    current = window["-DEVICE-"].get()
    if current in ports:
        selected = current
    else:
        selected = filt.default_input(ports) or ""
    window["-DEVICE-"].update(values=ports, value=selected)
    return ports


def set_running_ui(window, running):
    window["-DEVICE-"].update(disabled=running)
    window["-REFRESH-"].update(disabled=running)
    window["-START-"].update(disabled=running)
    window["-STOP-"].update(disabled=not running)


def parse_channel(value):
    try:
        channel = int(value)
    except (TypeError, ValueError):
        channel = 1
    return min(16, max(1, channel))


def main():
    setup_logging()
    logging.info("Application startup")

    layout = [
        [sg.Text(APP_NAME, font=("Helvetica", 16))],
        [
            sg.Text("Input device:"),
            sg.Combo(
                [],
                default_value="",
                key="-DEVICE-",
                size=(32, 1),
                readonly=True,
            ),
            sg.Button("Refresh", key="-REFRESH-"),
        ],
        [sg.Text("Output: %s" % VIRTUAL_PORT_NAME)],
        [
            sg.Checkbox(
                "Force output channel:",
                key="-FORCE-",
                enable_events=True,
            ),
            sg.Combo(
                [str(i) for i in range(1, 17)],
                default_value="1",
                key="-CHANNEL-",
                size=(4, 1),
                readonly=True,
                enable_events=True,
            ),
        ],
        [sg.Text("Breath CC:"), sg.Text("0", key="-BREATH-VALUE-", size=(4, 1))],
        [
            sg.Button("Start", key="-START-"),
            sg.Button("Stop", key="-STOP-", disabled=True),
        ],
        [sg.Text("Status:"), sg.Text("Stopped", key="-STATUS-", size=(50, 1))],
    ]

    window = sg.Window(APP_NAME, layout, finalize=True)
    filt = BreathFilter(window)
    refresh_devices(window, filt)

    try:
        filt.ensure_virtual_out()
    except Exception as exc:
        logging.exception("Failed to create virtual MIDI output")
        window["-STATUS-"].update("Error creating virtual output: %s" % exc)
        window["-START-"].update(disabled=True)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, None):
            break

        if event == "-FORCE-":
            filt.force_channel = bool(values["-FORCE-"])
        elif event == "-CHANNEL-":
            filt.channel = parse_channel(values["-CHANNEL-"])
        elif event == "-REFRESH-":
            refresh_devices(window, filt)
        elif event == "-START-":
            port_name = values["-DEVICE-"]
            if not port_name:
                window["-STATUS-"].update("No MIDI input device selected.")
                continue
            filt.force_channel = bool(values["-FORCE-"])
            filt.channel = parse_channel(values["-CHANNEL-"])
            try:
                filt.start(port_name)
            except Exception as exc:
                logging.exception("Failed to start")
                window["-STATUS-"].update(str(exc))
                continue
            window["-STATUS-"].update("Running")
            set_running_ui(window, True)
        elif event == "-STOP-":
            try:
                filt.stop()
            except Exception as exc:
                logging.exception("Failed to stop")
                window["-STATUS-"].update(str(exc))
                continue
            window["-STATUS-"].update("Stopped")
            set_running_ui(window, False)
        elif event == "-BREATH-":
            window["-BREATH-VALUE-"].update(str(values[event]))
        elif event == "-ERROR-":
            window["-STATUS-"].update(str(values[event]))

    logging.info("Application exit")
    try:
        filt.close()
    except Exception:
        logging.exception("Error during shutdown")
    window.close()


if __name__ == "__main__":
    main()
