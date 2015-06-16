import os
import sys


def isproject(path):
    """Return whether or not `path` is a project

    Arguments:
        path (str): Absolute path

    """

    if os.path.basename(path)[0] in (".", "_"):
        return False
    if not os.path.isdir(path):
        return False
    if not any(fname in os.listdir(path)
               for fname in ("templates.yaml",
                             "inventory.yaml")):
        return False
    return True


def echo(text, silent=False, newline=True):
    if silent:
        return
    print(text) if newline else sys.stdout.write(text)
