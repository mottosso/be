# be subshell, do not call directly.
if ! [ "$BE_ENTER" = "" ]; then cd $BE_DEVELOPMENTDIR; fi

# Run script
if ! [ "$BE_SCRIPT" = "" ];then . $BE_SCRIPT;fi

bash
