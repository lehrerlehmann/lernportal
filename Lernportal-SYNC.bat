@echo off
cd /d "%~dp0"

echo === Lernportal synchronisieren ===
echo.

echo [1/4] Lade aktuelle Version von GitHub...
git pull
if errorlevel 1 goto error

echo.
echo [2/4] Fuege lokale Aenderungen hinzu...
git add .

echo.
set /p msg=Beschreibung der Aenderung: 
if "%msg%"=="" set msg=Lernportal aktualisiert

echo.
echo [3/4] Erstelle Commit...
git commit -m "%msg%"

echo.
echo [4/4] Lade zu GitHub hoch...
git push
if errorlevel 1 goto error

echo.
echo ==============================
echo Lernportal ist synchronisiert!
echo ==============================
pause
exit

:error
echo.
echo FEHLER: Synchronisierung nicht erfolgreich.
echo Bitte Fehlermeldung oben ansehen.
pause