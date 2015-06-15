:: Dash Subshell, do not call directly.
@ECHO OFF
REM Be Prompt 1.0

TITLE ...%BE_DEVELOPMENTDIR:~-40% - %BE_PROJECT% / %BE_ITEM% / %BE_TYPE%
CD %BE_DEVELOPMENTDIR%
CMD /F:ON /Q /K