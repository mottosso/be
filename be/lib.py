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

self = sys.modules[__name__]
self._parent = None


def parent():
    """Determine subshell matching the currently running shell

    The shell is determined by either a pre-defined BE_SHELL
    environment variable, or, if none is found, via psutil
    which looks at the parent process directly through
    system-level calls.

    For example, is `be` is run from cmd.exe, then the full
    path to cmd.exe is returned, and the same goes for bash.exe
    and bash (without suffix) for Unix environments.

    The point is to return an appropriate subshell for the
    running shell, as opposed to the currently running OS.

    """

    if self._parent:
        return self._parent

    if "BE_SHELL" in os.environ:
        self._parent = os.environ["BE_SHELL"]
    else:
        # If a shell is not provided, rely on `psutil`
        # to look at the calling process name.
        try:
            import psutil
        except ImportError:
            raise ImportError(
                "No shell provided, see documentation for "
                "BE_SHELL for more information.\n"
                "https://github.com/mottosso/be/wiki"
                "/environment#read-environment-variables")

        parent = psutil.Process(os.getpid()).parent()

        basename = os.path.basename(parent.exe())
        if "be" in basename:
            parent = parent.parent()

        self._parent = str(parent.exe())

    return self._parent


def platform():
    """Return platform for the current shell, e.g. windows or unix"""
    executable = parent()
    basename = os.path.basename(executable)
    basename, _ = os.path.splitext(basename)

    if basename in ("bash", "sh"):
        return "unix"
    if basename in ("cmd", "powershell"):
        return "windows"

    raise SystemError("Unsupported shell")


def cmd(parent):
    """Determine subshell command for subprocess.call

    Arguments:
        parent (str): Absolute path to parent shell executable

    """

    shell_name = os.path.basename(parent).rsplit(".", 1)[0]

    dirname = os.path.dirname(__file__)

    # Support for Bash
    if shell_name in ("bash", "sh"):
        shell = os.path.join(dirname, "_shell.sh").replace("\\", "/")
        cmd = [parent.replace("\\", "/"), shell]

    # Support for Cmd
    elif shell_name in ("cmd",):
        shell = os.path.join(dirname, "_shell.bat").replace("\\", "/")
        cmd = [parent, "/K", shell]

    # Support for Powershell
    elif shell_name in ("powershell",):
        raise SystemError("Powershell not yet supported")

    # Unsupported
    else:
        raise SystemError("Unsupported shell: %s" % shell_name)

    return cmd


def context(project=""):
    """Produce the be environment

    The environment is an exact replica of the active
    environment of the current process, with a few
    additional variables, all of which are listed below.

    The `be` environment are considered "defaults" that
    may be overwritten by the incoming environment, with
    the exception of BE_CWD which must always be the
    real current working directory.

    """

    environment = os.environ.copy()
    environment.update({
        "BE_PROJECT": project,
        "BE_PROJECTROOT": (
            os.path.join(_extern.cwd(), project).replace("\\", "/")
            if project else ""),
        "BE_PROJECTSROOT": _extern.cwd(),
        "BE_ALIASDIR": "",
        "BE_CWD": _extern.cwd(),
        "BE_CD": "",
        "BE_ROOT": "",
        "BE_TOPICS": "",
        "BE_DEVELOPMENTDIR": "",
        "BE_ACTIVE": "1",
        "BE_USER": "",
        "BE_SCRIPT": "",
        "BE_PYTHON": "",
        "BE_ENTER": "",
        "BE_TEMPDIR": "",
        "BE_PRESETSDIR": "",
        "BE_GITHUB_API_TOKEN": "",
        "BE_ENVIRONMENT": "",
        "BE_BINDING": "",
        "BE_TABCOMPLETION": ""
    })

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
    projects = list()
    for project in sorted(os.listdir(_extern.cwd())):
        abspath = os.path.join(_extern.cwd(), project)
        if not isproject(abspath):
            continue
        projects.append(project)
    return projects


def list_inventory(project):
    inventory = _extern.load_inventory(project)
    inverted = _format.invert_inventory(inventory)
    items = list()
    for item in sorted(inverted, key=lambda a: (inverted[a], a)):
        items.append((item, inverted[item]))
    return items


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
        return []

    except IndexError as exc:
        raise IndexError("At least %s topics are required" % str(exc))

    fields = _format.replacement_fields_from_context(context(project))
    binding = _format.binding_from_item(inventory, item)
    pattern = _format.pattern_from_template(templates, binding)

    # 2 arguments, {1}/{2}/{3} -> {1}/{2}
    # 2 arguments, {1}/{2}/assets/{3} -> {1}/{2}/assets
    index_end = pattern.index(str(len(topics)-1)) + 2
    trimmed_pattern = pattern[:index_end]

    # If there aren't any more positional arguments, we're done
    if not re.findall("{[\d]+}", pattern[index_end:]):
        return []

    # Append trail
    # e.g. {1}/{2}/assets
    #             ^^^^^^^
    try:
        index_trail = pattern[index_end:].index("{")
        trail = pattern[index_end:index_end + index_trail - 1]
        trimmed_pattern += trail
    except ValueError:
        pass

    try:
        path = trimmed_pattern.format(*topics, **fields)
    except IndexError:
        raise IndexError("Template for \"%s\" has unordered "
                         "positional arguments: \"%s\"" % (item, pattern))

    if not os.path.isdir(path):
        return []

    items = list()
    for dirname in os.listdir(path):
        if not os.path.isdir(os.path.join(path, dirname)):
            continue

        items.append(dirname)

    return items
