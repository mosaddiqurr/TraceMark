. "$PSScriptRoot/common.ps1"
Invoke-Checked '.venv/Scripts/python.exe' @('-m','ruff','check','apps','packages','tests','scripts')
Invoke-Checked '.venv/Scripts/python.exe' @('-m','ruff','format','--check','apps','packages','tests','scripts')
Invoke-Checked '.venv/Scripts/python.exe' @('-m','mypy','apps/api/tracemark_api','packages/watermark_engine/src','scripts')
Invoke-Checked 'pnpm.cmd' @('--dir','apps/web','lint')
Invoke-Checked 'pnpm.cmd' @('--dir','apps/web','typecheck')
Invoke-Checked 'pnpm.cmd' @('--dir','apps/web','format:check')
