param(
  [switch]$DryRun
)

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $repo

$old = "scripts/sherlock_api.py"
$new = "scripts/qingniao_be_api.py"

if (Test-Path $old) {
  Write-Host "ERROR: $old still exists, expected removed" -ForegroundColor Red
  exit 1
}

if (!(Test-Path $new)) {
  Write-Host "ERROR: $new missing" -ForegroundColor Red
  exit 1
}

# Grep-like search for references
Write-Host "Scanning for old name references..."
$hits = rg -n "sherlock_api" | Out-String
if ($hits) {
  Write-Host "Found references to 'sherlock_api':" -ForegroundColor Yellow
  Write-Host $hits
} else {
  Write-Host "OK: no stray references found."
}

Write-Host "Done."
