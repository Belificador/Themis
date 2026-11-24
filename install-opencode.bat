@echo off
setlocal EnableExtensions
title Instalador de OpenCode

set "DEST=%LOCALAPPDATA%\opencode"
set "ZIP=%TEMP%\opencode.zip"

rem Detectar arquitectura (x64 / arm64)
set "ARCH=x64"
if /i "%PROCESSOR_ARCHITECTURE%"=="AMD64" set "ARCH=x64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARCH=arm64"
if /i "%PROCESSOR_ARCHITEW6432%"=="AMD64" set "ARCH=x64"
if /i "%PROCESSOR_ARCHITEW6432%"=="ARM64" set "ARCH=arm64"

set "URL=https://opencode.ai/update/api/latest/cli/opencode/opencode-windows-%ARCH%.zip"

echo.
echo ==========================================
echo   Instalando OpenCode  (%ARCH%)
echo   Destino: %DEST%
echo ==========================================
echo.

if not exist "%DEST%" mkdir "%DEST%" >nul 2>&1

echo [1/4] Descargando...
curl.exe -L --fail --progress-bar "%URL%" -o "%ZIP%"
if errorlevel 1 goto :err

echo [2/4] Extrayendo...
tar -xf "%ZIP%" -C "%DEST%" >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%DEST%' -Force"
  if errorlevel 1 goto :err
)
del /q "%ZIP%" >nul 2>&1

if not exist "%DEST%\opencode.exe" goto :notfound

echo [3/4] Agregando al PATH del usuario...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d='%DEST%'; $p=[Environment]::GetEnvironmentVariable('Path','User'); if ($null -eq $p) { $p='' }; if ($p -notlike ('*'+$d+'*')) { [Environment]::SetEnvironmentVariable('Path', ($p.TrimEnd(';')+';'+$d), 'User') }"

set "PATH=%DEST%;%PATH%"

echo [4/4] Verificando...
"%DEST%\opencode.exe" --version
if errorlevel 1 goto :err

echo.
echo ==========================================
echo   Listo. OpenCode instalado correctamente.
echo   Cierra y abre una terminal NUEVA
echo   para poder usar el comando: opencode
echo ==========================================
echo.
pause
exit /b 0

:err
echo.
echo ERROR: la instalacion fallo. Revisa tu conexion o antivirus.
echo URL usada: %URL%
echo.
pause
exit /b 1

:notfound
echo.
echo ERROR: no se encontro opencode.exe despues de extraer.
echo.
pause
exit /b 1
