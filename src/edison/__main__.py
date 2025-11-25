"""Allow running Edison as a module: python -m edison"""

import sys

from edison.cli._dispatcher import main

if __name__ == "__main__":
    sys.exit(main())
