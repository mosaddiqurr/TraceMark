. "$PSScriptRoot/common.ps1"
if (-not (Test-Path -LiteralPath '.venv')) { Invoke-Checked 'py' @('-3.12','-m','venv','.venv') }
Invoke-Checked '.venv/Scripts/python.exe' @('-m','pip','install','-r','requirements.txt','-e','./packages/watermark_engine[test,forensics]','-e','./apps/api[dev]')
Invoke-Checked 'pnpm.cmd' @('install','--frozen-lockfile')
Invoke-Checked '.venv/Scripts/python.exe' @('scripts/prepare_assets.py')
Invoke-Checked '.venv/Scripts/python.exe' @('scripts/init_secrets.py')
Write-Host 'Ready: run scripts/api.ps1 and pnpm --dir apps/web dev in separate terminals.'
