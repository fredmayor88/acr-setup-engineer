# Car-setups skill — common developer tasks.
# Requires: Python 3, git. Works on Mac, Linux, WSL, and Git Bash on Windows.
#
# Targets:
#   make test        run the full test suite
#   make zip         rebuild dist/car-setups-skill.zip (commit changes first)
#   make check-zip   list ZIP entries — verify forward slashes + expected files
#   make release     create a GitHub draft release with the ZIP asset (edit TAG first)
#   make all         test + zip (default)

TAG ?= v0.1.0

.PHONY: all test zip check-zip release

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

release:
	git tag $(TAG)
	git push origin $(TAG)
	gh release create $(TAG) dist/car-setups-skill.zip \
	  --title "$(TAG)" \
	  --notes-file RELEASE_NOTES.md \
	  --draft
