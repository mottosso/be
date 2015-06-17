# be subshell, do not call directly.
if ! [ -z ${BE_ENTER+x} ]; then cd $BE_DEVELOPMENTDIR; fi

# Run script
if ! [ -z ${BE_SCRIPT+x} ]; then . $BE_SCRIPT; fi

bash
