# Car-setups skill — common developer tasks.
# Requires: Python 3, git. Works on Mac, Linux, WSL, and Git Bash on Windows.
# Dev/test dependencies (PyYAML): pip install -r requirements-dev.txt
#
# Targets:
#   make test        run the full test suite
#   make zip         rebuild dist/car-setups-skill.zip (commit changes first)
#   make check-zip   list ZIP entries — verify forward slashes + expected files
#   make release     create a GitHub draft release with the ZIP asset (edit TAG first)
#   make all         test + zip (default)

TAG ?= v0.1.0
VERSION_FILE := .claude/skills/car-setups/VERSION

.PHONY: all test zip check-zip release stamp-version

all: test zip

test:
	python -m unittest discover -s tests -v

zip:
	python -c "import os; os.makedirs('dist', exist_ok=True)"
	git archive --format=zip --prefix=car-setups/ HEAD:.claude/skills/car-setups \
	  -o dist/car-setups-skill.zip
	@echo "Built dist/car-setups-skill.zip"

check-zip:
	python check_zip.py

# Stamps the release tag into VERSION and commits it, so the archived ZIP (built from HEAD's
# committed tree, not from a tag ref) self-reports the released version instead of "dev".
stamp-version:
	echo $(TAG) > $(VERSION_FILE)
	git add $(VERSION_FILE)
	git commit -m "release: stamp VERSION to $(TAG)"

release: stamp-version test zip
	git tag $(TAG)
	git push origin main $(TAG)
	gh release create $(TAG) dist/car-setups-skill.zip \
	  --title "$(TAG)" \
	  --notes-file RELEASE_NOTES.md \
	  --draft
