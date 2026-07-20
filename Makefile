.PHONY: setup dev up down lint test benchmark demo seed clean status

setup:
	powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

dev:
	powershell -ExecutionPolicy Bypass -File scripts/dev.ps1

up:
	docker compose up --build

down:
	docker compose down

lint:
	powershell -ExecutionPolicy Bypass -File scripts/lint.ps1

test:
	powershell -ExecutionPolicy Bypass -File scripts/test.ps1

benchmark:
	powershell -ExecutionPolicy Bypass -File scripts/benchmark.ps1

demo:
	powershell -ExecutionPolicy Bypass -File scripts/demo.ps1

seed:
	.venv/Scripts/python -m tracemark_api.cli seed

clean:
	powershell -ExecutionPolicy Bypass -File scripts/clean.ps1

status:
	docker compose ps
