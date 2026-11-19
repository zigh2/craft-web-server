"""Entry point for frozen (PyInstaller) builds: run.py [serve|update|passwd|version]."""
import sys

from craftweb.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
