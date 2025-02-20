PROJECT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

TESTS := $(PROJECT)tests
ALL := $(SRC) $(TESTS)

export PYTHONPATH = $(PROJECT)
export PY_COLORS=1

# Update uv.lock with the latest deps
lock:
	uv lock --upgrade --no-cache

# Generate requirements.txt from pyproject.toml
requirements:
	uv export --frozen --no-hashes --format=requirements-txt -o requirements.txt

# Run integration tests
integration:
	uv run --frozen --isolated --extra dev \
		pytest \
		--verbose \
		--exitfirst \
		--capture=no \
		--tb native \
		--log-cli-level=INFO \
		$(TESTS)/integration \
		$(ARGS)
