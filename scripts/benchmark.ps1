$ErrorActionPreference = 'Stop'

& .\.venv\Scripts\python.exe scripts\generate_dataset.py
& .\.venv\Scripts\python.exe scripts\run_benchmark.py --profile quick
