import os
import sys
import random

import _data


def random_name():
    """Return a random name

    Example:
        >> random_name()
        dizzy_badge
        >> random_name()
        evasive_cactus

    """

    adj = _data.adjectives[random.randint(0, len(_data.adjectives) - 1)]
    noun = _data.nouns[random.randint(0, len(_data.nouns) - 1)]
    return "%s_%s" % (adj, noun)


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
