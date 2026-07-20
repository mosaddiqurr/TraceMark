$ErrorActionPreference = 'Stop'

& .\.venv\Scripts\python.exe -m pytest
pnpm --dir apps/web test -- --run
