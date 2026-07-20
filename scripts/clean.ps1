$ErrorActionPreference = 'Stop'

$targets = @('artifacts', 'tmp', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'apps/web/dist', 'playwright-report', 'test-results')
$workspaceRoot = (Resolve-Path -LiteralPath '.').Path

foreach ($target in $targets) {
    $candidate = Join-Path $workspaceRoot $target
    if (Test-Path -LiteralPath $candidate) {
        $resolved = (Resolve-Path -LiteralPath $candidate).Path
        if (-not $resolved.StartsWith($workspaceRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove path outside workspace: $resolved"
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}

Write-Host 'Removed generated artifacts. Persistent Docker volumes were not removed.'
