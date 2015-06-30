import re
import os
import sys
import random

import _data
import _extern
import _format

NORMAL = 0
PROGRAM_ERROR = 1
USER_ERROR = 2
PROJECT_ERROR = 3
TEMPLATE_ERROR = 4

# Topic syntaxes
FIXED = 1 << 0
POSITIONAL = 1 << 1


def context(project):
    environment = {
        "BE_PROJECT": project,
        "BE_ALIASDIR": "",
        "BE_CWD": _extern.cwd(),
        "BE_CD": "",
        "BE_ROOT": "",
        "BE_TOPICS": "",
        "BE_DEVELOPMENTDIR": "",
        "BE_PROJECTROOT": os.path.join(
            _extern.cwd(), project).replace("\\", "/"),
        "BE_PROJECTSROOT": _extern.cwd(),
        "BE_ACTIVE": "True",
        "BE_USER": "",
        "BE_SCRIPT": "",
        "BE_PYTHON": "",
        "BE_ENTER": "0",
        "BE_TEMPDIR": "",
        "BE_PRESETSDIR": "",
        "BE_GITHUB_API_TOKEN": "",
        "BE_ENVIRONMENT": "",
        "BE_BINDING": ""
    }
    environment.update(os.environ)

    return environment


def map_redirect(redirect, topics, environment):
    """Map environment variables from `remap` key to their values

    Arguments:
        redirect (dict): Source/destination pairs, e.g. {BE_ACTIVE: ACTIVE}
        topics (tuple): Topics from which to sample, e.g. (project, item, task)
        environment (dict): Environmnent from which to sample

    """

    for map_source, map_dest in redirect.items():
        if re.match("{\d+}", map_source):
            topics_index = int(map_source.strip("{}"))
            topics_value = topics[topics_index]
            environment[map_dest] = topics_value
            continue

        environment[map_dest] = environment[map_source]


def write_aliases(aliases, path):
    """Write user-supplied aliases

    Arguments:
        aliases (list): Supplied aliases
        path (str): Absolute path to where aliases are to be written

    """

    # Default "home" alias
    home_alias = ("cd %BE_DEVELOPMENTDIR%"
                  if os.name == "nt" else "cd $BE_DEVELOPMENTDIR")
    aliases["home"] = home_alias

    return _extern.write_aliases(aliases, path)


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

    try:
        if os.path.basename(path)[0] in (".", "_"):
            return False
        if not os.path.isdir(path):
            return False
        if not any(fname in os.listdir(path)
                   for fname in ("templates.yaml",
                                 "inventory.yaml")):
            return False
    except:
        return False

    return True


def echo(text, silent=False, newline=True):
    if silent:
        return
    print(text) if newline else sys.stdout.write(text)
