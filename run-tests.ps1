[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$projectRoot = $PSScriptRoot
$javaRoot = Join-Path $projectRoot "java-version"
$failedSuites = [System.Collections.Generic.List[string]]::new()

function Write-Section([string] $title) {
    Write-Host ""
    Write-Host ("=" * 72) -ForegroundColor DarkGray
    Write-Host ("  " + $title) -ForegroundColor Cyan
    Write-Host ("=" * 72) -ForegroundColor DarkGray
}

Write-Section "PYTHON UNIT TESTS"
$pythonCandidates = @(
    (Join-Path $projectRoot ".venv\Scripts\python.exe"),
    (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
    (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique

$pythonCommand = $null
foreach ($candidate in $pythonCandidates) {
    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & $candidate -c "import pytest" 2>$null
    $ErrorActionPreference = $previousErrorAction
    if ($LASTEXITCODE -eq 0) {
        $pythonCommand = $candidate
        break
    }
}

if ($null -eq $pythonCommand) {
    Write-Host "  [SKIP] pytest is not installed. Run: python -m pip install -r requirements.txt" -ForegroundColor Yellow
    $failedSuites.Add("Python")
} else {
    & $pythonCommand -m pytest (Join-Path $projectRoot "tests") -v --tb=short
    if ($LASTEXITCODE -ne 0) {
        $failedSuites.Add("Python")
    }
}

Write-Section "JAVA UNIT TESTS"
$mavenCommand = Get-Command mvn -ErrorAction SilentlyContinue
$javaExitCode = 1
if ($null -eq $mavenCommand) {
    Write-Host "  [SKIP] Maven is not installed or is not available on PATH." -ForegroundColor Yellow
} else {
    Push-Location $javaRoot
    try {
        & $mavenCommand.Source -q test
        $javaExitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
}

$javaPassed = 0
$javaFailed = 0
$reportPath = Join-Path $javaRoot "target\surefire-reports"
$reportFiles = if ($null -ne $mavenCommand) {
    Get-ChildItem -Path $reportPath -Filter "TEST-*.xml" -ErrorAction SilentlyContinue
} else {
    @()
}
foreach ($reportFile in $reportFiles) {
    [xml] $report = Get-Content -Raw -LiteralPath $reportFile.FullName
    foreach ($testCase in $report.testsuite.testcase) {
        $hasFailure = ($null -ne $testCase.failure) -or ($null -ne $testCase.error)
        if ($hasFailure) {
            $javaFailed++
            Write-Host ("  [FAIL] {0}" -f $testCase.name) -ForegroundColor Red
        } else {
            $javaPassed++
            Write-Host ("  [PASS] {0}" -f $testCase.name) -ForegroundColor Green
        }
    }
}
Write-Host ("`n  Java result: {0} passed, {1} failed" -f $javaPassed, $javaFailed)

if (($javaExitCode -ne 0) -or ($javaFailed -gt 0)) {
    $failedSuites.Add("Java")
}

Write-Section "FINAL RESULT"
if ($failedSuites.Count -eq 0) {
    Write-Host "  ALL TEST SUITES PASSED" -ForegroundColor Green
    exit 0
}

Write-Host ("  FAILED: " + ($failedSuites -join ", ")) -ForegroundColor Red
exit 1
