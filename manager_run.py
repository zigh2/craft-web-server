"""Entry point of CraftManager.exe (windowed build): opens the simple control panel."""
import sys

from craftweb.manager import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
