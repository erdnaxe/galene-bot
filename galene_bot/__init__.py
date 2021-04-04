# Copyright (C) 2021 Alexandre Iooss
# SPDX-License-Identifier: MIT

"""
Bots for Galène.
"""

try:
    from galene_bot.version import version as __version__
except ImportError:
    __version__ = "dev"

from base_argparse import ArgumentParser
from base_bot import GaleneBot

# See https://www.python.org/dev/peps/pep-0008/#module-level-dunder-names
__all__ = [
    "__version__",
    "ArgumentParser",
    "GaleneBot",
]
