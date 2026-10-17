. "$PSScriptRoot/common.ps1"

$targets = @('artifacts', 'tmp', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.tmp-tests', '.validation-cache', '.codex-test-temp', 'datasets/generated', 'apps/web/dist', 'apps/web/playwright-report', 'apps/web/test-results', 'apps/web/journey-results', 'playwright-report', 'test-results', '.coverage')
$workspaceRoot = (Resolve-Path -LiteralPath '.').Path
$workspacePrefix = $workspaceRoot + [System.IO.Path]::DirectorySeparatorChar
$cleanupFailures = [System.Collections.Generic.List[string]]::new()

$targets += @(Get-ChildItem -LiteralPath apps,packages,scripts,tests -Directory -Recurse -Filter __pycache__ | Select-Object -ExpandProperty FullName)

foreach ($target in $targets) {
    $candidate = if ([System.IO.Path]::IsPathRooted($target)) { $target } else { Join-Path $workspaceRoot $target }
    if (Test-Path -LiteralPath $candidate) {
        $resolved = (Resolve-Path -LiteralPath $candidate).Path
        if (-not $resolved.StartsWith($workspacePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove path outside workspace: $resolved"
        }
        if ((Get-Item -LiteralPath $resolved -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to recursively remove a linked directory: $resolved"
        }
        try {
            Remove-Item -LiteralPath $resolved -Recurse -Force
        } catch {
            $cleanupFailures.Add($resolved)
            Write-Warning "Could not remove generated target: $resolved"
        }
    }
}

Write-Host 'Removed generated artifacts. Local secrets, dependencies and trace metadata remain private and ignored.'
if ($cleanupFailures.Count -gt 0) {
    throw 'Some generated targets could not be removed. Review the warnings; they remain excluded from publication.'
}
