"""Entry point for Sonic Bloom."""

import sys


def main():
    # Suppress PyObjC app icon in the dock
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyProhibited
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyProhibited)
    except ImportError:
        pass

    from dotenv import load_dotenv
    load_dotenv()

    from sonic_bloom.app import SonicBloom
    app = SonicBloom()
    try:
        app.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
