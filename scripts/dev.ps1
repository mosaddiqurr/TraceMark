$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
    Write-Warning 'Created .env from local defaults. Generate application keys before shared use.'
}

python scripts\init_secrets.py
docker compose up --build
