"""
This module controls a projector relay connected to a Raspberry Pi Zero.
The Pi Zero is exposed to the main Raspberry Pi 4 via USB in gadget mode,
and GPIO control is achieved through the pigpio library. The default
IP address of the Pi Zero is ``192.168.7.2``; update this if your setup
differs.

Previously this module relied on CircuitPython's ``digitalio`` and ``board``
modules. Those do not work when the code is executed on the Pi 4 and the
device is physically attached to a remote Pi Zero. The updated version
instead uses pigpio to toggle a BCM pin on the remote device. The pin
number corresponds to ``board.D25`` (BCM 25).
"""

import pigpio
import time

# BCM pin used to toggle the projector. ``board.D25`` translates to BCM 25.
PROJECTOR_GPIO = 25


class Projector:
    """Toggle a projector connected to a remote Raspberry Pi Zero via pigpio.

    Parameters
    ----------
    host : str, optional
        IP address or hostname of the pigpio daemon on the Pi Zero.
        Defaults to ``"192.168.7.2"``.
    """

    def __init__(self, host: str = "192.168.7.2") -> None:
        # Connect to the remote pigpio daemon. If the connection fails,
        # ``pigpio.pi`` returns an object with ``connected`` set to 0.
        self.pi = pigpio.pi(host)
        if not self.pi.connected:
            raise RuntimeError(f"Failed to connect to pigpio daemon on {host}")

        # Configure the projector GPIO as an output and start with it off.
        self.pin = PROJECTOR_GPIO
        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.on = False
        self.pi.write(self.pin, 0)

    def switch(self) -> None:
        """Toggle the projector on/off."""
        self.on = not self.on
        self.pi.write(self.pin, 1 if self.on else 0)

    def stop(self) -> None:
        """Ensure the projector is off and clean up the pigpio connection."""
        self.pi.write(self.pin, 0)
        self.pi.stop()


if __name__ == "__main__":
    p = Projector()
    try:
        while True:
            p.switch()
            time.sleep(1)
    finally:
        p.stop()
