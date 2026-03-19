@echo off
title TwitterYoldas Preview
cd /d "%~dp0"

echo.
echo  TwitterYoldas baslatiliyor...
echo  Preview  : http://localhost:7731
echo  Kutuphane: http://localhost:7731/library
echo.

start "" http://localhost:7731/library
python preview/server.py
