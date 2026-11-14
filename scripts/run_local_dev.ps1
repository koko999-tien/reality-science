<#
.SYNOPSIS
    REALITY SCIENCE — Local Development Orchestrator for Windows/PowerShell
.DESCRIPTION
    Validates pre-flight requirements and launches services locally when Docker daemon is absent.
.PARAMETER Component
    The component to run: "All", "Backend", "Worker", "Frontend", "Verify"
#>
param (
    [ValidateSet("All", "Backend", "Worker", "Frontend", "Verify")]
    [string]$Component = "Verify"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path "$RepoRoot\PROJECT.md")) {
    $RepoRoot = "D:\Reality_Science"
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  REALITY SCIENCE — Local Development Orchestrator" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

function Test-PreFlight {
    Write-Host "[*] Checking Python environment..." -ForegroundColor Yellow
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        Write-Error "Python is not found on PATH."
    }
    $pyVer = & python --version
    Write-Host "[PASS] Python: $pyVer" -ForegroundColor Green

    Write-Host "[*] Checking Node.js environment..." -ForegroundColor Yellow
    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) {
        Write-Error "Node.js is not found on PATH."
    }
    $nodeVer = & node --version
    Write-Host "[PASS] Node.js: $nodeVer" -ForegroundColor Green

    Write-Host "[*] Checking Docker availability..." -ForegroundColor Yellow
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if ($docker) {
        Write-Host "[INFO] Docker CLI is available." -ForegroundColor Green
    } else {
        Write-Host "[WARN] Docker CLI is NOT installed. Running in local standalone mode." -ForegroundColor Yellow
    }

    Write-Host "[*] Checking Infrastructure Ports..." -ForegroundColor Yellow
    $pgCheck = Test-NetConnection -ComputerName localhost -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($pgCheck) {
        Write-Host "[PASS] PostgreSQL listening on port 5432" -ForegroundColor Green
    } else {
        Write-Host "[WARN] PostgreSQL not detected on port 5432. Start local PG or Docker." -ForegroundColor Yellow
    }

    $redisCheck = Test-NetConnection -ComputerName localhost -Port 6379 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($redisCheck) {
        Write-Host "[PASS] Redis listening on port 6379" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Redis not detected on port 6379. Start local Redis or Docker." -ForegroundColor Yellow
    }

    Write-Host "[*] Checking Zero-Secret Environment Templates..." -ForegroundColor Yellow
    $envFiles = @(
        "$RepoRoot\.env.example",
        "$RepoRoot\backend\.env.example",
        "$RepoRoot\worker\.env.example",
        "$RepoRoot\frontend\.env.example"
    )
    foreach ($f in $envFiles) {
        if (Test-Path $f) {
            Write-Host "  [OK] $([System.IO.Path]::GetFileName($f))" -ForegroundColor Green
        } else {
            Write-Error "Missing template file: $f"
        }
    }

    # Worker Zero Database Invariant
    $workerEnv = Get-Content "$RepoRoot\worker\.env.example"
    $uncommented = $workerEnv | Where-Object { $_ -match '\S' -and -not $_.StartsWith('#') }
    $dbVars = $uncommented | Where-Object { $_ -match 'DATABASE_URL' -or $_ -match 'POSTGRES' }
    if ($dbVars) {
        Write-Error "Worker .env.example VIOLATION: Database credentials detected!"
    } else {
        Write-Host "[PASS] Worker Zero-Database Invariant Verified." -ForegroundColor Green
    }

    # Dependency Lockfiles
    Write-Host "[*] Checking Dependency Lockfiles..." -ForegroundColor Yellow
    $lockFiles = @(
        "$RepoRoot\shared\requirements.lock",
        "$RepoRoot\backend\requirements.lock",
        "$RepoRoot\worker\requirements.lock",
        "$RepoRoot\frontend\package-lock.json"
    )
    foreach ($lf in $lockFiles) {
        if (Test-Path $lf) {
            Write-Host "  [OK] $([System.IO.Path]::GetFileName($lf))" -ForegroundColor Green
        } else {
            Write-Error "Missing lockfile: $lf"
        }
    }
}

Test-PreFlight

if ($Component -eq "Verify") {
    Write-Host "`nPre-flight verification completed successfully." -ForegroundColor Cyan
    exit 0
} elseif ($Component -eq "Backend") {
    Write-Host "`nStarting FastAPI Backend..." -ForegroundColor Cyan
    Set-Location "$RepoRoot\backend"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
} elseif ($Component -eq "Worker") {
    Write-Host "`nStarting Celery Compute Worker..." -ForegroundColor Cyan
    Set-Location "$RepoRoot\worker"
    python -m celery -A worker.celery_app worker -Q compute_tasks --concurrency=1 --pool=solo --loglevel=info
} elseif ($Component -eq "Frontend") {
    Write-Host "`nStarting Next.js Frontend..." -ForegroundColor Cyan
    Set-Location "$RepoRoot\frontend"
    npm run dev
}
