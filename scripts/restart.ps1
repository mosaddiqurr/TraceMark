. "$PSScriptRoot/common.ps1"
Invoke-Checked '.venv/Scripts/python.exe' @('scripts/check_restart.py')
