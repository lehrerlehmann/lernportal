@echo off
cd /d "%~dp0"

echo Fuege alle Aenderungen hinzu...
git add .

echo.
set /p msg=Beschreibung der Aenderung: 

if "%msg%"=="" set msg=Lernportal aktualisiert

git commit -m "%msg%"

echo.
echo Lade zu GitHub hoch...
git push

echo.
echo Fertig.
pause