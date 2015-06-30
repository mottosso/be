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


def list_projects():
    for project in sorted(os.listdir(_extern.cwd())):
        abspath = os.path.join(_extern.cwd(), project)
        if not isproject(abspath):
            continue
        yield project


def list_inventory(project):
    inventory = _extern.load_inventory(project)
    inverted = _format.invert_inventory(inventory)
    for item in sorted(inverted, key=lambda a: (inverted[a], a)):
        yield item, inverted[item]


def list_pattern(topics):
    project = topics[0]

    be = _extern.load_be(project)
    templates = _extern.load_templates(project)
    inventory = _extern.load_inventory(project)

    # Get item
    try:
        key = be.get("templates", {}).get("key") or "{1}"
        item = _format.item_from_topics(key, topics)
        binding = _format.binding_from_item(inventory, item)

    except KeyError:
        return

    except IndexError as exc:
        raise IndexError("At least %s topics are required" % str(exc))

    fields = _format.replacement_fields_from_context(context(project))
    binding = _format.binding_from_item(inventory, item)
    pattern = _format.pattern_from_template(templates, binding)

    trimmed_pattern = pattern[:pattern.index(str(len(topics)-1)) + 2]

    try:
        path = trimmed_pattern.format(*topics, **fields)
    except IndexError:
        raise IndexError("Template for \"%s\" has unordered "
                         "positional arguments: \"%s\"" % (item, pattern))

    if not os.path.isdir(path):
        return

    for dirname in os.listdir(path):
        if not os.path.isdir(os.path.join(path, dirname)):
            continue

        yield dirname
