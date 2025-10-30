# Publish to Production PyPI Script
# This script cleans old builds, creates new distribution packages, and uploads to PyPI

Write-Host "🧹 Cleaning old builds..." -ForegroundColor Cyan

# Remove old build artifacts
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
    Write-Host "  ✓ Removed dist/" -ForegroundColor Green
}

if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
    Write-Host "  ✓ Removed build/" -ForegroundColor Green
}

if (Test-Path "src/git_commit_mcp.egg-info") {
    Remove-Item -Recurse -Force "src/git_commit_mcp.egg-info"
    Write-Host "  ✓ Removed egg-info/" -ForegroundColor Green
}

Write-Host ""
Write-Host "📦 Building distribution packages..." -ForegroundColor Cyan

# Build the package
python -m build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "  ✓ Build successful!" -ForegroundColor Green
Write-Host ""

# Check the package
Write-Host "🔍 Checking package..." -ForegroundColor Cyan
twine check dist/*

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Package check failed!" -ForegroundColor Red
    exit 1
}

Write-Host "  ✓ Package check passed!" -ForegroundColor Green
Write-Host ""

# Upload to PyPI
Write-Host "🚀 Uploading to PyPI..." -ForegroundColor Cyan
Write-Host "  (You will be prompted for your PyPI API token)" -ForegroundColor Yellow
Write-Host ""

twine upload dist/*

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Upload failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Successfully published to PyPI!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "  1. View your package: https://pypi.org/project/git-commit-mcp-server/" -ForegroundColor White
Write-Host "  2. Test installation: pipx install git-commit-mcp-server" -ForegroundColor White
Write-Host ""
