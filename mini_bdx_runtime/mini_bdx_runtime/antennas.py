"""
Servo control for the duck's antennas using a remote Raspberry Pi Zero.

In the previous implementation this module used CircuitPython's ``pwmio``
module to produce PWM signals on the local GPIO pins (``board.D13`` and
``board.D12``). In the new setup the antennas are physically connected to
a Pi Zero that is exposed via USB gadget mode. We therefore use the
pigpio library to send servo pulse widths to the remote pins over the
network. This allows the controlling code to run on the Pi 4 while
driving servos attached to the Pi Zero.

The servo angle is specified in the range [-1, 1], where -1 corresponds
to the minimum position (1 ms pulse), 0 corresponds to the neutral
position (1.5 ms pulse) and 1 corresponds to the maximum position
(2 ms pulse). These values are converted into microsecond pulse widths
for ``pi.set_servo_pulsewidth``.
"""

import pigpio
import math
import time

# BCM pin numbers for the left and right antenna servos on the Pi Zero.
# ``board.D13`` → BCM 13, ``board.D12`` → BCM 12.
LEFT_ANTENNA_PIN = 13
RIGHT_ANTENNA_PIN = 12
LEFT_SIGN = 1
RIGHT_SIGN = -1
# Minimum update interval when sweeping the antennas (20 ms).
MIN_UPDATE_INTERVAL = 1 / 50


def value_to_pulse_width(value: float) -> int:
    """Map a value in [-1, 1] to a servo pulse width in microseconds.

    A value of 0 returns the neutral pulse width of 1500 µs. Values of -1
    and 1 return 1000 µs and 2000 µs respectively. The result is
    clamped to [500, 2500] µs which is within the pigpio servo limits.
    """
    # Clamp input range
    v = max(-1.0, min(1.0, value))
    return int(1500 + (v * 500))


class Antennas:
    """Control left and right servo antennas via a remote pigpio daemon.

    Parameters
    ----------
    host : str, optional
        IP address or hostname of the pigpio daemon running on the Pi Zero.
        Defaults to ``"192.168.7.2"``.
    """

    def __init__(self, host: str = "192.168.7.2") -> None:
        # Connect to remote pigpio
        self.pi = pigpio.pi(host)
        if not self.pi.connected:
            raise RuntimeError(f"Failed to connect to pigpio daemon on {host}")

        # Store pins and set to servo mode (pigpio automatically sets mode)
        self.left_pin = LEFT_ANTENNA_PIN
        self.right_pin = RIGHT_ANTENNA_PIN
        # Initialise servos to neutral position
        neutral = value_to_pulse_width(0)
        self.pi.set_servo_pulsewidth(self.left_pin, neutral)
        self.pi.set_servo_pulsewidth(self.right_pin, neutral)

    def set_position_left(self, position: float) -> None:
        self.set_position(self.left_pin, position, LEFT_SIGN)

    def set_position_right(self, position: float) -> None:
        self.set_position(self.right_pin, position, RIGHT_SIGN)

    def set_position(self, pin: int, value: float, sign: int = 1) -> None:
        """Set the servo on ``pin`` to ``value`` (clamped to [-1, 1])."""
        if -1.0 <= value <= 1.0:
            pulse_width = value_to_pulse_width(value * sign)
            self.pi.set_servo_pulsewidth(pin, pulse_width)
        else:
            print("Invalid input! Enter a value between -1 and 1.")

    def stop(self) -> None:
        """Centre the servos and close the pigpio connection."""
        time.sleep(MIN_UPDATE_INTERVAL)
        # Centre both servos
        self.set_position_left(0)
        self.set_position_right(0)
        time.sleep(MIN_UPDATE_INTERVAL)
        # Disable servo pulses and close connection
        self.pi.set_servo_pulsewidth(self.left_pin, 0)
        self.pi.set_servo_pulsewidth(self.right_pin, 0)
        self.pi.stop()


if __name__ == "__main__":
    antennas = Antennas()

    try:
        start_time = time.monotonic()
        current_time = start_time

        while current_time - start_time < 5:
            value = math.sin(2 * math.pi * 1 * current_time)
            antennas.set_position_left(value)
            antennas.set_position_right(value)
            time.sleep(MIN_UPDATE_INTERVAL)
            current_time = time.monotonic()

    finally:
        antennas.stop()