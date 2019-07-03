_be () {
  COMPREPLY=();

  local cur=${COMP_WORDS[COMP_CWORD]}

  if [ ${COMP_CWORD} -ge 2 ]; then
    if [ ${COMP_WORDS[1]} == "in" ]; then

      # Determine whether the last-entered
      # argument is complete. $cur will either
      # be empty, or contain the currently
      # entered characters.
      local complete_=1
      if [ ${#cur} -ne 0 ]; then
        complete_=0
      fi

      local opts=$(be tab $COMP_LINE $complete_)
      COMPREPLY=($(compgen -W "${opts}" $cur))
    fi
  fi

  return 0
}

complete -F _be -o bashdefault be
