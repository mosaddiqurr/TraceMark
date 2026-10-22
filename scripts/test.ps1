. "$PSScriptRoot/common.ps1"
$testRunId = [guid]::NewGuid().ToString('N')
New-Item -ItemType Directory -Force '.tmp-tests' | Out-Null
Invoke-Checked '.venv/Scripts/python.exe' @('-m','pytest',"--basetemp=.tmp-tests/pytest-$testRunId",'-o',"cache_dir=.validation-cache/pytest-$testRunId",'--cov=apps/api/tracemark_api','--cov=packages/watermark_engine/src/tracemark_watermark','--cov-report=term-missing','--cov-fail-under=75')
Invoke-Checked 'pnpm.cmd' @('--dir','apps/web','test')
