:: be subshell, do not call directly.
@ECHO OFF
REM Be Prompt 1.0

TITLE %BE_TOPIC%

:: Enter development directory
if not "%BE_ENTER%" == "" CD %BE_DEVELOPMENTDIR%

:: Run script
if not "%BE_SCRIPT%" == "" call %BE_SCRIPT%

CMD /F:ON /Q /K