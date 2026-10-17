.PHONY: setup api dev lint test benchmark restart clean
PYTHON ?= python
PNPM ?= pnpm

ifeq ($(OS),Windows_NT)
PYTHON = .venv/Scripts/python.exe
PNPM = pnpm.cmd
endif

# Each run owns its temp tree; stale Windows ACLs cannot break later runs.
TEST_RUN_ID := $(shell "$(PYTHON)" -c "import uuid; print(uuid.uuid4().hex)")
TEST_TMP_DIR ?= .tmp-tests/pytest-make-$(TEST_RUN_ID)
TEST_CACHE_DIR ?= .validation-cache/pytest-make-$(TEST_RUN_ID)

setup:
	$(PYTHON) -m pip install -r requirements.txt -e './packages/watermark_engine[test,forensics]' -e './apps/api[dev]'
	$(PNPM) install --frozen-lockfile
	$(PYTHON) scripts/prepare_assets.py
	$(PYTHON) scripts/init_secrets.py

api:
	$(PYTHON) -m uvicorn tracemark_api.main:create_app --factory --env-file .env --host 127.0.0.1 --port 8000 --no-access-log

dev:
	$(PNPM) --dir apps/web dev

lint:
	$(PYTHON) -m ruff check apps packages tests scripts
	$(PYTHON) -m ruff format --check apps packages tests scripts
	$(PYTHON) -m mypy apps/api/tracemark_api packages/watermark_engine/src scripts
	$(PNPM) --dir apps/web lint
	$(PNPM) --dir apps/web typecheck
	$(PNPM) --dir apps/web format:check

test:
	$(PYTHON) -m pytest --basetemp=$(TEST_TMP_DIR) -o cache_dir=$(TEST_CACHE_DIR) --cov=apps/api/tracemark_api --cov=packages/watermark_engine/src/tracemark_watermark --cov-report=term-missing --cov-fail-under=75
	$(PNPM) --dir apps/web test

benchmark:
	$(PYTHON) scripts/generate_dataset.py
	$(PYTHON) scripts/run_benchmark.py --profile quick

restart:
	$(PYTHON) scripts/check_restart.py

clean:
	powershell -ExecutionPolicy Bypass -File scripts/clean.ps1
