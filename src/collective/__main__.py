"""`python -m collective` — same CLI as the installed collective script."""

import sys

from .cli import main

sys.exit(main())
