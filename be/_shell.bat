:: be subshell, do not call directly.
@ECHO OFF
REM Be Prompt 1.0

TITLE ...%BE_DEVELOPMENTDIR:~-40% - %BE_PROJECT% / %BE_ITEM% / %BE_TYPE%
CD %BE_DEVELOPMENTDIR%

:: Run script
if not "%BE_SCRIPT%" == "" call %BE_SCRIPT%

CMD /F:ON /Q /K