# ACR Setup Engineer skill — common developer tasks.
# Requires: Python 3, git. Works on Mac, Linux, WSL, and on Windows from both Git Bash and
# PowerShell/cmd — recipes avoid shell-specific syntax because make picks cmd.exe when invoked
# from PowerShell. Tested against GNU Make 3.81, so no make >= 4.0 features (e.g. `$(file <...)`).
# Dev/test dependencies (PyYAML): pip install -r requirements-dev.txt
#
# Targets:
#   make test        run the full test suite
#   make charts      regenerate every car chart (all three kinds)
#   make car-lab     regenerate the ACR Car Lab data in ../acr-car-lab
#   make charts-power        power/torque curves, and each template's engine_curve block
#   make charts-gearing      "where each gear tops out" ladders
#   make charts-final-drive  primary gear x differential ratio
#   make zip         rebuild dist/acr-setup-engineer-skill-<version>.zip (commit changes first)
#   make check-zip   verify ZIP entries + that the filename version matches VERSION inside
#   make release     create a GitHub draft release with the ZIP asset (edit TAG first)
#   make clean       remove dist/
#   make all         test + zip (default)

TAG ?= v0.1.0
VERSION_FILE := .claude/skills/acr-setup-engineer/VERSION

# Version baked into the ZIP filename. Read from HEAD rather than the working tree because `zip`
# archives HEAD — so the filename always matches the VERSION file *inside* the archive.
# Recursively expanded (=, not :=) so `release` sees the tag that stamp-version just committed,
# rather than the value from when make started.
#
# Done in Python, not shell: make picks its own shell, and on Windows that is cmd.exe when make is
# invoked from PowerShell — where `2>/dev/null` and `||` are not valid and silently yield "dev".
# Python is already a hard dependency, and this one-liner has no shell metacharacters.
SKILL_VERSION = $(shell python -c "import subprocess as s; r = s.run(['git','show','HEAD:$(VERSION_FILE)'], capture_output=True, text=True); print(r.stdout.strip() or 'dev')")
ZIP = dist/acr-setup-engineer-skill-$(SKILL_VERSION).zip

.PHONY: all test zip check-zip release stamp-version clean charts charts-power \
        charts-gearing charts-final-drive car-lab

all: test zip

test:
	python -m unittest discover -s tests -v

zip:
	python -c "import os; os.makedirs('dist', exist_ok=True)"
	git archive --format=zip --prefix=acr-setup-engineer/ HEAD:.claude/skills/acr-setup-engineer \
	  -o $(ZIP)
	@echo "Built $(ZIP)"

check-zip:
	python check_zip.py $(ZIP)

clean:
	python -c "import shutil; shutil.rmtree('dist', ignore_errors=True)"

# Chart regeneration. All three read the installed game's pak files, so they only run on a
# machine with Assetto Corsa Rally; pass --paks to either script if it is not at the default
# Steam location. Re-run after a game update, then read the diff.
charts: charts-power charts-gearing charts-final-drive

charts-power:
	python tools/torque-curves/extract_torque_curves.py

charts-gearing:
	python tools/gearing-charts/make_gearing_chart.py --all --charts gearing

charts-final-drive:
	python tools/gearing-charts/make_gearing_chart.py --all --charts final-drive

# Regenerates every ACR Car Lab JSON and page shell into the sibling acr-car-lab
# checkout. Reads the installed game's paks, so it only runs on a machine with
# Assetto Corsa Rally. Re-run after a game update, then commit in acr-car-lab. The game
# version in the site footer is read from the paks too (ProjectVersion in DefaultGame.ini).
car-lab:
	python tools/gearing-charts/export_car_data.py --all

# Stamps the release tag into VERSION and commits it, so the archived ZIP (built from HEAD's
# committed tree, not from a tag ref) self-reports the released version instead of "dev".
stamp-version:
	python -c "open(r'$(VERSION_FILE)', 'w', newline='\n').write('$(TAG)\n')"
	git add $(VERSION_FILE)
	git commit -m "release: stamp VERSION to $(TAG)"

release: stamp-version test zip
	git tag $(TAG)
	git push origin main $(TAG)
	gh release create $(TAG) $(ZIP) \
	  --title "$(TAG)" \
	  --notes-file RELEASE_NOTES.md \
	  --draft
