$ErrorActionPreference = 'Stop'

& .\.venv\Scripts\python.exe -m ruff check apps packages workers tests
& .\.venv\Scripts\python.exe -m mypy apps\api\tracemark_api packages\watermark_engine\src workers
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
