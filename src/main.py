"""App entry point.

Keep this file tiny: it should just wire things together and start the UI.
"""

from gui import start_gui


def main() -> None:
    start_gui()


if __name__ == "__main__":
    main()
