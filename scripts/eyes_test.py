import argparse
import time
from mini_bdx_runtime.eyes import Eyes


def main() -> None:
    """Test script to cycle the robot's eye colours."""
    parser = argparse.ArgumentParser(
        description="Cycle through eye colours for testing"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="IP address or hostname of the pigpio daemon",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port number of the pigpio daemon",
    )
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay between colour changes in seconds")
    args = parser.parse_args()

    try:
        eyes = Eyes(
            host=args.host,
            port=args.port,
            blink_duration=0.0,
            min_interval=1.0,
            max_interval=1.0,
        )
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
