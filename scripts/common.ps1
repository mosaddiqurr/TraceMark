$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

function Invoke-Checked {
    param([string]$CommandPath, [string[]]$CommandArguments)
    & $CommandPath @CommandArguments
    if ($LASTEXITCODE -ne 0) { throw "$CommandPath exited with code $LASTEXITCODE" }
}
