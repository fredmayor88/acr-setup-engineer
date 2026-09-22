#!/usr/bin/env python3
"""Write the installed game's version into the skill's GAME_VERSION file.

The number people call the game by (`0.6`) is ProjectVersion in acr/Config/DefaultGame.ini,
read out of the paks by tools/gearing-charts/game_version.py. This tool writes its display form
to .claude/skills/acr-setup-engineer/GAME_VERSION — the one place the skill, the extractors and
the tests read the current game version from. Run it first in `make extract`.

Usage:
  python write_game_version.py [--paks DIR]          # read the game, write GAME_VERSION
  python write_game_version.py --check [--paks DIR]  # exit 1 when GAME_VERSION differs from the game
  --version X.Y and --file PATH bypass the game and the default file (tests).
"""
import argparse
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'gearing-charts'))
from game_version import read_game_version  # noqa: E402

DEFAULT_PAKS = ('C:/Program Files (x86)/Steam/steamapps/common/'
                'Assetto Corsa Rally/acr/Content/Paks')
DEFAULT_FILE = os.path.join(HERE, '..', '..', '.claude', 'skills', 'acr-setup-engineer',
                            'GAME_VERSION')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--paks', default=DEFAULT_PAKS)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--version', help=argparse.SUPPRESS)
    ap.add_argument('--file', default=DEFAULT_FILE, help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.version:
        version = args.version
    else:
        if not os.path.isdir(args.paks):
            sys.exit(f'ACR paks not found at {args.paks} (pass --paks)')
        with tempfile.TemporaryDirectory() as tmp:
            version = read_game_version(args.paks, tmp)

    if args.check:
        current = ''
        if os.path.exists(args.file):
            with open(args.file, encoding='utf-8') as f:
                current = f.read().strip()
        if current != version:
            sys.stderr.write(f'GAME_VERSION says {current!r}, the game says {version!r}\n')
            return 1
        print(f'GAME_VERSION {version}: up to date')
        return 0
    with open(args.file, 'w', encoding='utf-8', newline='\n') as f:
        f.write(version + '\n')
    print(f'GAME_VERSION <- {version}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
