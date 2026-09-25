param (
    [string]$message = ""
)

if (-not $message) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $message = "Auto-update: $timestamp"
}

Write-Host "Staging changes..." -ForegroundColor Cyan
git add -A

$status = git status --porcelain
if ($status) {
    Write-Host "Committing changes with message: '$message'..." -ForegroundColor Cyan
    git commit -m "$message"
    
    Write-Host "Pushing to GitHub (origin main)..." -ForegroundColor Cyan
    git push origin main
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Successfully pushed to GitHub!" -ForegroundColor Green
    } else {
        Write-Host "Push failed. Please check network/credentials." -ForegroundColor Red
    }
} else {
    Write-Host "No changes to commit. Working tree clean." -ForegroundColor Yellow
}
