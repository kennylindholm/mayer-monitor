#!/bin/env bash

set -e

# Run the test suite using pytest
pytest tests/ --maxfail=1 --disable-warnings -v
