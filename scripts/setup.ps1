$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath '.venv')) {
    py -3.12 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e '.\packages\watermark_engine[forensics]' -e '.\apps\api[dev]'
pnpm install --frozen-lockfile=$false

Write-Host 'TraceMark dependencies are installed.'
