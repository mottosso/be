# DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
# export BASH_ENV=$DIR/_autocomplete.sh

# be subshell, do not call directly.
if ! [ "$BE_ENTER" = "" ]; then cd $BE_DEVELOPMENTDIR; fi

# Run script
if ! [ "$BE_SCRIPT" = "" ];then . $BE_SCRIPT;fi

# if [ "$BE_TABCOMPLETION" = "1" ]; then
#     # Run whichever shell called us
#     "$BE_SHELL"
# fi

"$BE_SHELL"
