import zipfile, sys

z = zipfile.ZipFile("dist/car-setups-skill.zip")
names = z.namelist()
errors = []

for n in names:
    if "\\" in n:
        errors.append(f"backslash in path: {n}")

if "car-setups/SKILL.md" not in names:
    errors.append("SKILL.md missing")

if not any(n.startswith("car-setups/car-templates/") and n.endswith(".yaml") for n in names):
    errors.append("no car-templates/*.yaml found")

for n in names:
    print(n)

if errors:
    print("\nERRORS:", file=sys.stderr)
    for e in errors:
        print(f"  {e}", file=sys.stderr)
    sys.exit(1)

print("\ncheck-zip no errors, OK")
