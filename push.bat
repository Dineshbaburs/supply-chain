@echo off
setlocal
set "MSG=%~1"
if "%MSG%"=="" set "MSG=Auto-update: %DATE% %TIME%"
git add -A
git commit -m "%MSG%"
git push origin main
echo Done.
