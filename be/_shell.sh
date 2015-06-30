# be subshell, do not call directly.
if ! [ "$BE_ENTER" = "" ]; then cd $BE_DEVELOPMENTDIR; fi

# Run script
if ! [ "$BE_SCRIPT" = "" ];then . $BE_SCRIPT;fi

# Tab completion
_be () {
  COMPREPLY=();

  local cur=${COMP_WORDS[COMP_CWORD]}
  
  if [ ${COMP_CWORD} -ge 2 ]; then
    if [ ${COMP_WORDS[1]} == "in" ]; then
      local opts=$(be tab $COMP_LINE)
      COMPREPLY=($(compgen -W "${opts}" $cur))
    fi
  fi

  return 0
}

complete -F _be -o default be

bash
