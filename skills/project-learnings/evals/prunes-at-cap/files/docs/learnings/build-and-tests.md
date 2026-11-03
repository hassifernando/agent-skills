# Build and tests

## Run `make test` instead of calling pytest directly
- why: pytest alone skips the fixtures that `make test` generates, so 12 tests fail with missing-file errors
- evidence: `Makefile` target test
- scope: project
- added: 2026-09-10
- verified: 2026-10-20

## Keep the legacy importer out of the unit test run
- why: the importer hits the network and makes the suite flaky
- evidence: `app/legacy_importer.py` and `tests/legacy/test_importer.py`
- scope: project
- added: 2026-09-10
- verified: 2026-10-20

## Pin the parser to version 2 in `requirements.txt`
- why: version 3 changes the date format and breaks `parse_date`
- evidence: `requirements.txt`
- scope: project
- added: 2026-09-10
- verified: 2026-10-20

