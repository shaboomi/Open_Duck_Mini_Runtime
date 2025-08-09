"""
Update: This module has been modified to use the pigpio library for driving
the eye LEDs on a remote Raspberry Pi Zero. The Pi Zero is connected to
the main Raspberry Pi 4 via USB (gadget mode) and exposes its GPIO pins over
the network using the pigpio daemon. The IP address of the Pi Zero must
be supplied when creating the `Eyes` instance (defaults to ``192.168.7.2``).

Instead of using CircuitPython's ``digitalio`` and ``board`` modules, we
instantiate a ``pigpio.pi`` object and configure the relevant pins as
outputs. The pins are referenced using their Broadcom (BCM) numbers, which
match the ``board.Dxx`` naming convention used previously (e.g. ``board.D24``
corresponds to BCM 24).

To blink the LEDs, this class writes a high (1) or low (0) value to both
pins using ``pi.write``. When stopping, the pins are explicitly set low and
the pigpio connection is terminated.
"""

import pigpio
import random
import time
from threading import Thread, Event

# BCM pin numbers corresponding to the eye LEDs on the Pi Zero. These match
# the ``board.Dxx`` names previously used (D24 → BCM 24, D23 → BCM 23).
LEFT_EYE_PIN = 24
RIGHT_EYE_PIN = 23


class Eyes:
    """Controls blinking of two eye LEDs via a remote pigpio daemon.

    Parameters
    ----------
    host : str, optional
        IP address or hostname of the pigpio daemon running on the Pi Zero.
        Defaults to ``"192.168.7.2"``. Change this if your Pi Zero uses a
        different IP address.
    blink_duration : float, optional
        Duration (in seconds) that the eyes remain closed for each blink.
    min_interval : float, optional
        Minimum time (in seconds) between blinks.
    max_interval : float, optional
        Maximum time (in seconds) between blinks.
    """

    def __init__(self, host: str = "192.168.7.2", blink_duration: float = 0.1,
                 min_interval: float = 1.0, max_interval: float = 4.0) -> None:
        # Establish a remote connection to the pigpio daemon running on the
        # Raspberry Pi Zero. If the connection fails, ``pigpio.pi`` will
        # return an object with ``connected`` set to 0.
        self.pi = pigpio.pi(host)
        if not self.pi.connected:
            raise RuntimeError(f"Failed to connect to pigpio daemon on {host}")

        # Configure the eye pins as outputs and start with the LEDs off.
        self.left_pin = LEFT_EYE_PIN
        self.right_pin = RIGHT_EYE_PIN
        self.pi.set_mode(self.left_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.right_pin, pigpio.OUTPUT)
        self.pi.write(self.left_pin, 0)
        self.pi.write(self.right_pin, 0)

        self.blink_duration: float = blink_duration
        self.min_interval: float = min_interval
        self.max_interval: float = max_interval

        # Threading setup for blinking logic.
        self._stop_event: Event = Event()
        self._thread: Thread = Thread(target=self.run, daemon=True)
        self._thread.start()

    def _set_eyes(self, state: bool) -> None:
        """Set both eye LEDs on (True) or off (False)."""
        value = 1 if state else 0
        self.pi.write(self.left_pin, value)
        self.pi.write(self.right_pin, value)

    def run(self):
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

    def stop(self):
        """Stop the blinking thread and release resources."""
        self._stop_event.set()
        self._thread.join()
        # Ensure the LEDs are turned off before closing the connection.
        self._set_eyes(False)
        # Terminate connection to the pigpio daemon.
        self.pi.stop()


if __name__ == "__main__":
    e = Eyes()
    try:
        while True:
            time.sleep(1)
    finally:
        e.stop()

