# be subshell, do not call directly.
cd $BE_DEVELOPMENTDIR

# Run script
if ! [ "$BE_SCRIPT" = "" ];then . $BE_SCRIPT;fi

bash
