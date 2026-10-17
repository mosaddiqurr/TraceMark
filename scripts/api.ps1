. "$PSScriptRoot/common.ps1"
Invoke-Checked '.venv/Scripts/python.exe' @('-m','uvicorn','tracemark_api.main:create_app','--factory','--env-file','.env','--host','127.0.0.1','--port','8000','--no-access-log')
