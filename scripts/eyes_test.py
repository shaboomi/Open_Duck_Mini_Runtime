import time
import argparse
from mini_bdx_runtime.eyes import Eyes


def main() -> None:
    """Test script to cycle the robot's eye colours."""
    parser = argparse.ArgumentParser(description="Cycle through eye colours for testing")
    parser.add_argument("--host", type=str, default="192.168.7.2",
                        help="IP address or hostname of the pigpio daemon on the Pi Zero")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay between colour changes in seconds")
    args = parser.parse_args()

    try:
        eyes = Eyes(host=args.host, blink_duration=0.0,
                    min_interval=1.0, max_interval=1.0)
    except RuntimeError as exc:
        print(f"Eyes initialisation failed: {exc}")
        return

    try:
        while True:
            eyes.cycle_color()
            time.sleep(args.delay)
    except KeyboardInterrupt:
        pass
    finally:
        eyes.stop()


if __name__ == "__main__":
    main()
