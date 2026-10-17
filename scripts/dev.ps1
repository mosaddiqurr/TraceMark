. "$PSScriptRoot/common.ps1"
Invoke-Checked 'pnpm.cmd' @('--dir','apps/web','dev')
