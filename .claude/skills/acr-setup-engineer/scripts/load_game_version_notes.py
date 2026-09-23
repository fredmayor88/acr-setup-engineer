#!/usr/bin/env python3
"""Find the tuning notes for the current game version.

Some tuning knowledge is true for one game version only (tyre pressure targets, which compound
lasts a stage). It ships as `game-versions/<version>.md`, hand-written, one file per version.
Every workflow that loads guideline layers runs this once and reads the file it names.

Usage:
  python scripts/load_game_version_notes.py                 # notes for the skill's GAME_VERSION
  python scripts/load_game_version_notes.py --version 0.6
  python scripts/load_game_version_notes.py --dir DIR       # notes folder (tests)

Output (stdout):
  line 1: the path of the notes file to read
  line 2 (only when the version has no file of its own): note: no notes for 0.6.1; using 0.6

Exit codes:
  0  a file was found (exact version, or the newest lower version)
  1  no file at or below the version — skip the layer and say so in one line
  2  usage error
"""
import os
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_DIR = os.path.join(SKILL_DIR, 'game-versions')
GAME_VERSION_FILE = os.path.join(SKILL_DIR, 'GAME_VERSION')

USAGE = ('Usage: load_game_version_notes.py [--version V] [--dir DIR]')


class NotesError(Exception):
    pass


def parse_version(text):
    """'0.6.1' -> (0, 6, 1); anything that is not dotted integers -> None."""
    parts = text.strip().split('.')
    if len(parts) < 2 or not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def available(directory):
    """Every <version>.md in directory, as (version tuple, version text, path), ascending."""
    found = []
    try:
        names = os.listdir(directory)
    except OSError as exc:
        raise NotesError(f'cannot read notes folder: {exc}')
    for name in names:
        if not name.endswith('.md'):
            continue
        version = parse_version(name[:-3])
        if version is not None:
            found.append((version, name[:-3], os.path.join(directory, name)))
    return sorted(found)


def resolve(version, directory):
    """The file for `version`: exact, else the newest lower one; None if nothing qualifies."""
    target = parse_version(version)
    if target is None:
        raise NotesError(f'not a version: {version!r}')
    candidates = [entry for entry in available(directory) if entry[0] <= target]
    return candidates[-1] if candidates else None


def read_game_version(path=GAME_VERSION_FILE):
    try:
        with open(path, encoding='utf-8') as fh:
            return fh.read().strip()
    except OSError as exc:
        raise NotesError(f'cannot read GAME_VERSION: {exc}')


def main():
    args = sys.argv[1:]
    version = None
    directory = NOTES_DIR
    i = 0
    while i < len(args):
        if args[i] == '--version' and i + 1 < len(args):
            version = args[i + 1]
            i += 2
        elif args[i] == '--dir' and i + 1 < len(args):
            directory = args[i + 1]
            i += 2
        else:
            print(f'unknown or incomplete option: {args[i]}\n{USAGE}', file=sys.stderr)
            return 2
    try:
        if version is None:
            version = read_game_version()
        entry = resolve(version, directory)
    except NotesError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if entry is None:
        print(f'no version notes for {version}', file=sys.stderr)
        return 1
    _, used, path = entry
    print(path)
    if parse_version(used) != parse_version(version):
        print(f'note: no notes for {version}; using {used}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
