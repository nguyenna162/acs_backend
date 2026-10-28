@echo off
title ACS Backend - AMR Fleet Controller (CNC Prod 2G)
echo ================================================================
echo    KHOI DONG HE THONG ACS BACKEND - VDA 5050 v2.1.0
echo    Khu vuc: CNC Prod 2G - Dieu khien & Quan ly AMR
echo ================================================================

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set PYTHON_CMD=.venv\Scripts\python.exe
) else if exist "venv\Scripts\python.exe" (
    set PYTHON_CMD=venv\Scripts\python.exe
) else (
    set PYTHON_CMD=python
)

echo [1/2] Dang kiem tra va ap dung migrations co so du lieu...
%PYTHON_CMD% manage.py migrate --noinput

echo [2/2] Dang khoi chay he thong bang acs_launch.py...
%PYTHON_CMD% acs_launch.py

pause
