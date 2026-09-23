import glob, re, sys, zipfile

PREFIX = "dist/acr-setup-engineer-skill-"

if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    matches = sorted(glob.glob(PREFIX + "*.zip"))
    if not matches:
        print("no ZIP in dist/ — run `make zip` first", file=sys.stderr)
        sys.exit(1)
    path = matches[-1]

try:
    z = zipfile.ZipFile(path)
except FileNotFoundError:
    print(f"{path} not found — run `make zip` first", file=sys.stderr)
    sys.exit(1)

names = z.namelist()
errors = []

for n in names:
    if "\\" in n:
        errors.append(f"backslash in path: {n}")

if "acr-setup-engineer/SKILL.md" not in names:
    errors.append("SKILL.md missing")

if not any(n.startswith("acr-setup-engineer/car-templates/") and n.endswith(".yaml") for n in names):
    errors.append("no car-templates/*.yaml found")

# The bundled default setups and the game version they were extracted from ship with the skill:
# build-setup step 4 anchors on car-setups/<slug>.yaml and stamps rows with GAME_VERSION, so a
# ZIP without them installs a skill that asks every user for default screenshots.
if not any(n.startswith("acr-setup-engineer/car-setups/") and n.endswith(".yaml") for n in names):
    errors.append("no car-setups/*.yaml found")

if "acr-setup-engineer/GAME_VERSION" not in names:
    errors.append("GAME_VERSION missing")

# The tuning notes for the current game version ship with the skill: every workflow reads
# game-versions/<version>.md as a guideline layer, so a ZIP without them tunes on stale rules.
if not any(n.startswith("acr-setup-engineer/game-versions/") and n.endswith(".md") for n in names):
    errors.append("no game-versions/*.md found")

# The version in the filename must match the VERSION file inside, or a published asset would
# advertise a version the skill doesn't self-report.
m = re.search(r"acr-setup-engineer-skill-(.+)\.zip$", path.replace("\\", "/"))
if not m:
    errors.append(f"filename does not encode a version: {path}")
elif "acr-setup-engineer/VERSION" not in names:
    errors.append("VERSION missing")
else:
    inner = z.read("acr-setup-engineer/VERSION").decode().strip()
    if inner != m.group(1):
        errors.append(f"filename version {m.group(1)!r} != VERSION inside {inner!r}")

print(f"checking {path}\n")
for n in names:
    print(n)

if errors:
    print("\nERRORS:", file=sys.stderr)
    for e in errors:
        print(f"  {e}", file=sys.stderr)
    sys.exit(1)

print("\ncheck-zip no errors, OK")
