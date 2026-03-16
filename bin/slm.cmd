@echo off
REM SuperLocalMemory V3 - Windows CLI (CMD variant)
REM Calls slm.bat for compatibility
call "%~dp0slm.bat" %*
exit /b %ERRORLEVEL%
