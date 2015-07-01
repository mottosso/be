# be subshell, do not call directly.

# Create a temporary file to which we will write
# the bash initialisation script.
TMPFILE=$(mktemp)
echo ". ~/.bashrc" > $TMPFILE

# Passed via --enter
if ! [ "$BE_ENTER" = "" ]; then
  echo "cd $BE_DEVELOPMENTDIR" >> $TMPFILE
else
  echo "cd $BE_CWD" >> $TMPFILE
fi

# Run script from be.yaml
if ! [ "$BE_SCRIPT" = "" ]; then
  echo ". $BE_SCRIPT" >> $TMPFILE; fi

# Source tab completion
if ! [ "$BE_TABCOMPLETION" = "" ]; then
  echo ". $BE_TABCOMPLETION" >> $TMPFILE; fi

# Add stuff to the temporary file
echo "rm -f $TMPFILE" >> $TMPFILE

# Start the new bash shell 
"$BE_SHELL" --rcfile $TMPFILE