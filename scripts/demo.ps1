$ErrorActionPreference = 'Stop'

python scripts\init_secrets.py
& .\.venv\Scripts\python.exe scripts\generate_dataset.py
docker compose up --build -d
docker compose exec api python -m tracemark_api.cli migrate
docker compose exec api python -m tracemark_api.cli seed
docker compose ps
