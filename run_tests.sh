#!/usr/bin/env bash

set -eou pipefail

# Run the test suite using pytest
pytest tests/ --maxfail=1 --disable-warnings -v
