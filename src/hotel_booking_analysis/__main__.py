"""Entry point for `python -m hotel_booking_analysis` (ADR-0006)."""

import os
import sys
from pathlib import Path

from hotel_booking_analysis.infrastructure.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdout.buffer, sys.stderr, Path.cwd(), os.environ))
