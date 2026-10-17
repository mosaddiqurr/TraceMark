. "$PSScriptRoot/common.ps1"
Invoke-Checked '.venv/Scripts/python.exe' @('scripts/generate_dataset.py')
Invoke-Checked '.venv/Scripts/python.exe' @('scripts/run_benchmark.py','--profile','quick')
