"""
This module provides an ``Eyes`` class capable of driving two WS2812 ("NeoPixel")
RGB LEDs connected to a Raspberry Pi Zero via the ``pigpio`` library.  It
replaces the earlier design which used two simple GPIO pins to blink the eyes.

The LEDs are connected in series to a single data pin (GPIO 23 on the Pi
Zero).  Each LED can be independently set to a 24‑bit colour.  The class
supports blinking with random intervals and cycling through a list of colours.

Usage example::

    from mini_bdx_runtime.eyes import Eyes

    eyes = Eyes(host="192.168.7.2")
    eyes.cycle_color()  # change to next colour
    # ... later ...
    eyes.stop()  # cleanly stop the blinking thread and pigpio

"""

import pigpio
import random
import time
from threading import Thread, Event, Lock
from typing import List, Tuple

# Single data pin for both WS2812 eye LEDs
DATA_PIN: int = 23

# Sequence of colours for cycling (RGB)
DEFAULT_COLOURS: List[Tuple[int, int, int]] = [
    (255, 255, 255),  # white
    (255, 0, 0),      # red
    (255, 165, 0),    # orange
    (0, 255, 0),      # green
    (0, 0, 255),      # blue
    (0, 255, 255),    # light blue
]


class Eyes:
    """Control and animate two WS2812 eye LEDs via a remote pigpio daemon."""

    def __init__(self, host: str = "192.168.7.2",
                 blink_duration: float = 0.1,
                 min_interval: float = 1.0,
                 max_interval: float = 4.0,
                 colours: List[Tuple[int, int, int]] | None = None) -> None:
        # Connect to the remote pigpiod
        port = pigpio.DEFAULT_PORT
        self.pi = pigpio.pi(host, port)
        if not self.pi.connected:
            raise RuntimeError(
                f"Failed to connect to pigpio daemon on {host}:{port}"
            )

        # Configure the single data pin
        self.data_pin = DATA_PIN
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)
        self.pi.write(self.data_pin, 0)

        # Blinking configuration
        self.blink_duration = blink_duration
        self.min_interval = min_interval
        self.max_interval = max_interval

        # Colour state
        self.colours = colours if colours else list(DEFAULT_COLOURS)
        self.color_index = 0
        self.current_color = self.colours[self.color_index]

        # Threading setup for blinking logic
        self._wave_lock = Lock()
        self._stop_event = Event()
        self._thread = Thread(target=self.run, daemon=True)
        self._thread.start()

    def _set_eyes(self, state: bool) -> None:
        """Set both eyes to the current colour if ``state`` is True, else off."""
        if state:
            self.set_color(self.current_color)
        else:
            self.set_color((0, 0, 0))

    def run(self) -> None:
        """Background blinking thread."""
        try:
            while not self._stop_event.is_set():
                self._set_eyes(False)
                time.sleep(self.blink_duration)
                self._set_eyes(True)
                next_blink = random.uniform(self.min_interval, self.max_interval)
                time.sleep(next_blink)
        except Exception as err:
            print(f"Error in eye thread: {err}")
            self._stop_event.set()

    def stop(self) -> None:
        """Stop the blinking thread and release pigpio resources."""
        self._stop_event.set()
        self._thread.join()
        self._set_eyes(False)
        self.pi.stop()

    # ------------------------------------------------------------------
    # Colour control API
    # ------------------------------------------------------------------
    def _build_wave(self, colour: Tuple[int, int, int]) -> List[pigpio.pulse]:
        """Construct pigpio waveform pulses for two WS2812 LEDs from an RGB colour."""
        red, green, blue = colour
        data_bytes = [green, red, blue] * 2
        pulses: List[pigpio.pulse] = []
        for byte in data_bytes:
            for bit in range(8):
                if byte & (1 << (7 - bit)):
                    # Logic‑1: longer high pulse
                    pulses.append(pigpio.pulse(1 << self.data_pin, 0, 2))
                    pulses.append(pigpio.pulse(0, 1 << self.data_pin, 1))
                else:
                    # Logic‑0: shorter high pulse
                    pulses.append(pigpio.pulse(1 << self.data_pin, 0, 1))
                    pulses.append(pigpio.pulse(0, 1 << self.data_pin, 2))
        # Latch period
        pulses.append(pigpio.pulse(0, 1 << self.data_pin, 50))
        return pulses

    def set_color(self, colour: Tuple[int, int, int]) -> None:
        """Send the given colour to both LEDs immediately."""
        with self._wave_lock:
            pulses = self._build_wave(colour)
            self.pi.wave_add_generic(pulses)
            wid = self.pi.wave_create()
            if wid < 0:
                raise RuntimeError("Failed to create WS2812 waveform")
            self.pi.wave_send_once(wid)
            while self.pi.wave_tx_busy():
                time.sleep(0.001)
            self.pi.wave_delete(wid)
        if colour != (0, 0, 0):
            self.current_color = colour

    def cycle_color(self) -> None:
        """Advance to the next colour and update the eyes."""
        self.color_index = (self.color_index + 1) % len(self.colours)
        self.current_color = self.colours[self.color_index]
        self.set_color(self.current_color)

    def get_current_color(self) -> Tuple[int, int, int]:
        """Return the currently selected RGB colour."""
        return self.current_color
