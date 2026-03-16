@echo off
REM SuperLocalMemory V3 - Windows CLI Wrapper
REM Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
REM Licensed under MIT License
REM Repository: https://github.com/qualixar/superlocalmemory

setlocal enabledelayedexpansion

REM Find Python 3
where python3 >/dev/null 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python3
    goto :run
)
where python >/dev/null 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python
    goto :run
)

echo Error: Python 3.11+ not found.
echo Install from: https://python.org/downloads/
exit /b 1

:run
%PYTHON_CMD% -m superlocalmemory.cli.main %*
exit /b %ERRORLEVEL%
