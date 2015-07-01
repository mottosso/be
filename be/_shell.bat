:: be subshell, do not call directly.
@ECHO OFF

:: Enter development directory
if not "%BE_ENTER%" == "" CD %BE_DEVELOPMENTDIR%

:: Run script
if not "%BE_SCRIPT%" == "" call %BE_SCRIPT%

%BE_SHELL% /K