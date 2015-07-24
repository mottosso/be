import re
import os
import sys
import random

from . import _data

# Exit codes
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

        # `pip install` creates an additional executable
        # that tricks the above mechanism to think of it
        # as the parent shell. See #34 for more.
        if parent.name() in ("be", "be.exe"):
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

    raise SystemError("Unsupported shell: %s" % basename)


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


def context(root, project=""):
    """Produce the be environment

    The environment is an exact replica of the active
    environment of the current process, with a few
    additional variables, all of which are listed below.

    """

    environment = os.environ.copy()
    environment.update({
        "BE_PROJECT": project,
        "BE_PROJECTROOT": (
            os.path.join(root, project).replace("\\", "/")
            if project else ""),
        "BE_PROJECTSROOT": root,
        "BE_ALIASDIR": "",
        "BE_CWD": root,
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
    """Print to the console

    Arguments:
        text (str): Text to print to the console
        silen (bool, optional): Whether or not to produce any output
        newline (bool, optional): Whether or not to append a newline.

    """

    if silent:
        return
    print(text) if newline else sys.stdout.write(text)


def list_projects(root, backend=os.listdir):
    """List projects at `root`

    Arguments:
        root (str): Absolute path to the `be` root directory,
            typically the current working directory.

    """
    projects = list()
    for project in sorted(backend(root)):
        abspath = os.path.join(root, project)
        if not isproject(abspath):
            continue
        projects.append(project)
    return projects


def list_inventory(inventory):
    """List a projects inventory

    Given a project, simply list the contents of `inventory.yaml`

    Arguments:
        root (str): Absolute path to the `be` root directory,
            typically the current working directory.
        inventory (dict): inventory.yaml

    """

    inverted = invert_inventory(inventory)
    items = list()
    for item in sorted(inverted, key=lambda a: (inverted[a], a)):
        items.append((item, inverted[item]))
    return items


def list_template(root, topics, templates, inventory, be, absolute=False):
    """List contents for resolved template

    Resolve a template as far as possible via the given `topics`.
    For example, if a template supports 5 arguments, but only
    3 are given, resolve the template until its 4th argument
    and list the contents thereafter.

    In some cases, an additional path is present following an
    argument, e.g. {3}/assets. The `/assets` portion is referred
    to as the "tail" and is appended also.

    Arguments:
        topics (tuple): Current topics
        templates (dict): templates.yaml
        inventory (dict): inventory.yaml
        be (dict): be.yaml

    """

    project = topics[0]

    # Get item
    try:
        key = be.get("templates", {}).get("key") or "{1}"
        item = item_from_topics(key, topics)
        binding = binding_from_item(inventory, item)

    except KeyError:
        return []

    except IndexError as exc:
        raise IndexError("At least %s topics are required" % str(exc))

    fields = replacement_fields_from_context(
        context(root, project))
    binding = binding_from_item(inventory, item)
    pattern = pattern_from_template(templates, binding)

    # 2 arguments, {1}/{2}/{3} -> {1}/{2}
    # 2 arguments, {1}/{2}/assets/{3} -> {1}/{2}/assets
    index_end = pattern.index(str(len(topics)-1)) + 2
    trimmed_pattern = pattern[:index_end]

    # If there aren't any more positional arguments, we're done
    print trimmed_pattern
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
        abspath = os.path.join(path, dirname).replace("\\", "/")
        if not os.path.isdir(abspath):
            continue

        if absolute:
            items.append(abspath)
        else:
            items.append(dirname)

    return items


def invert_inventory(inventory):
    """Return {item: binding} from {binding: item}

    Protect against items with additional metadata
    and items whose type is a number

    Returns:
        Dictionary of inverted inventory

    """

    inverted = dict()
    for binding, items in inventory.iteritems():
        for item in items:
            if isinstance(item, dict):
                item = item.keys()[0]
            item = str(item)  # Key may be number

            if item in inverted:
                echo("Warning: Duplicate item found, "
                     "for \"%s: %s\"" % (binding, item))
                continue
            inverted[item] = binding

    return inverted


self = sys.modules[__name__]
self.bindings = {}


def pos_development_directory(templates,
                              inventory,
                              context,
                              topics,
                              user,
                              item):
    """Return absolute path to development directory

    Arguments:
        templates (dict): templates.yaml
        inventory (dict): inventory.yaml
        context (dict): The be context, from context()
        topics (list): Arguments to `in`
        user (str): Current `be` user
        item (str): Item from template-binding address

    """

    replacement_fields = replacement_fields_from_context(context)
    binding = binding_from_item(inventory, item)
    pattern = pattern_from_template(templates, binding)

    positional_arguments = find_positional_arguments(pattern)
    highest_argument = find_highest_position(positional_arguments)
    highest_available = len(topics) - 1
    if highest_available < highest_argument:
        echo("Template for \"%s\" requires at least %i arguments" % (
            item, highest_argument + 1))
        sys.exit(USER_ERROR)

    try:
        return pattern.format(*topics, **replacement_fields).replace("\\", "/")
    except KeyError as exc:
        echo("TEMPLATE ERROR: %s is not an available key\n" % exc)
        echo("Available tokens:")
        for key in replacement_fields:
            echo("\n- %s" % key)
        sys.exit(TEMPLATE_ERROR)


def fixed_development_directory(templates, inventory, topics, user):
    """Return absolute path to development directory

    Arguments:
        templates (dict): templates.yaml
        inventory (dict): inventory.yaml
        context (dict): The be context, from context()
        topics (list): Arguments to `in`
        user (str): Current `be` user

    """

    echo("Fixed syntax has been deprecated, see positional syntax")

    project, item, task = topics[0].split("/")

    template = binding_from_item(inventory, item)
    pattern = pattern_from_template(templates, template)

    if find_positional_arguments(pattern):
        echo("\"%s\" uses a positional syntax" % project)
        echo("Try this:")
        echo("  be in %s" % " ".join([project, item, task]))
        sys.exit(USER_ERROR)

    keys = {
        "cwd": os.getcwd(),
        "project": project,
        "item": item.replace("\\", "/"),
        "user": user,
        "task": task,
        "type": task,  # deprecated
    }

    try:
        return pattern.format(**keys).replace("\\", "/")
    except KeyError as exc:
        echo("TEMPLATE ERROR: %s is not an available key\n" % exc)
        echo("Available keys")
        for key in keys:
            echo("\n- %s" % key)
        sys.exit(1)


def replacement_fields_from_context(context):
    """Convert context replacement fields

    Example:
        BE_KEY=value -> {"key": "value}

    Arguments:
        context (dict): The current context

    """

    return dict((k[3:].lower(), context[k])
                for k in context if k.startswith("BE_"))


def item_from_topics(key, topics):
    """Get binding from `topics` via `key`

    Example:
        {0} == hello --> be in hello world
        {1} == world --> be in hello world

    Returns:
        Single topic matching the key

    Raises:
        IndexError (int): With number of required
            arguments for the key

    """

    if re.match("{\d+}", key):
        pos = int(key.strip("{}"))
        try:
            binding = topics[pos]
        except IndexError:
            raise IndexError(pos + 1)

    else:
        echo("be.yaml template key not recognised")
        sys.exit(PROJECT_ERROR)

    return binding


def find_positional_arguments(pattern):
    """Turn a string of '{1} {2} {3}' into ('{1}', '{2}', '{3}')"""
    return re.findall("{\d?}", pattern)


def find_highest_position(topics):
    """Determine highest position in e.g. ('{2}', '{3}', '{1}')"""
    return int(sorted(topics)[-1].strip("{}"))


def project_dir(root, project):
    """Return absolute path to project given the name `project`

    ..note:: Assumed to root at the current working directory.

    Arguments:
        project (str): Name of project

    """

    return os.path.join(root, project)


def pattern_from_template(templates, name):
    """Return pattern for name

    Arguments:
        templates (dict): Current templates
        name (str): Name of name

    """

    if name not in templates:
        echo("No template named \"%s\"" % name)
        sys.exit(1)

    return templates[name]


def binding_from_item(inventory, item):
    """Return binding for `item`

    Example:
        asset:
        - myasset

        The binding is "asset"

    Arguments:
        project: Name of project
        item (str): Name of item

    """

    if item in self.bindings:
        return self.bindings[item]

    bindings = invert_inventory(inventory)

    try:
        self.bindings[item] = bindings[item]
        return bindings[item]

    except KeyError as exc:
        exc.bindings = bindings
        raise exc


def parse_environment(fields, context, topics):
    """Resolve the be.yaml environment key

    Features:
        - Lists, e.g. ["/path1", "/path2"]
        - Environment variable references, via $
        - Replacement field references, e.g. {key}
        - Topic references, e.g. {1}

    """

    def _resolve_environment_lists(context):
        """Concatenate environment lists"""
        for key, value in context.copy().iteritems():
            if isinstance(value, list):
                context[key] = os.pathsep.join(value)
        return context

    def _resolve_environment_references(fields, context):
        """Resolve $ occurences by expansion

        Given a dictionary {"PATH": "$PATH;somevalue;{0}"}
        Return {"PATH": "value_of_PATH;somevalue;myproject"},
        given that the first topic - {0} - is "myproject"

        Arguments:
            fields (dict): Environment from be.yaml
            context (dict): Source context

        """

        def repl(match):
            key = pattern[match.start():match.end()].strip("$")
            if key not in context:
                sys.stderr.write("ERROR: Unavailable "
                                 "fields variable: \"%s\"" % key)
                sys.exit(USER_ERROR)
            return context[key]

        pat = re.compile("\$\w+", re.IGNORECASE)
        for key, pattern in fields.copy().iteritems():
            fields[key] = pat.sub(repl, pattern)

        return fields

    def _resolve_environment_fields(fields, context, topics):
        """Resolve {} occurences

        Supports both positional and BE_-prefixed variables.

        Example:
            BE_MYKEY -> "{mykey}" from `BE_MYKEY`
            {1} -> "{mytask}" from `be in myproject mytask`

        Returns:
            Dictionary of resolved fields

        """

        source_dict = replacement_fields_from_context(context)
        source_dict.update(dict((str(topics.index(topic)), topic)
                                for topic in topics))

        def repl(match):
            key = pattern[match.start():match.end()].strip("{}")
            try:
                return source_dict[key]
            except KeyError:
                echo("PROJECT ERROR: Unavailable reference \"%s\" "
                     "in be.yaml" % key)
                sys.exit(PROJECT_ERROR)

        for key, pattern in fields.copy().iteritems():
            fields[key] = re.sub("{[\d\w]+}", repl, pattern)

        return fields

    fields = _resolve_environment_lists(fields)
    fields = _resolve_environment_references(fields, context)
    fields = _resolve_environment_fields(fields, context, topics)

    return fields


def parse_redirect(redirect, topics, context):
    """Resolve the be.yaml redirect key

    Arguments:
        redirect (dict): Source/destination pairs, e.g. {BE_ACTIVE: ACTIVE}
        topics (tuple): Topics from which to sample, e.g. (project, item, task)
        context (dict): Context from which to sample

    """

    for map_source, map_dest in redirect.items():
        if re.match("{\d+}", map_source):
            topics_index = int(map_source.strip("{}"))
            topics_value = topics[topics_index]
            context[map_dest] = topics_value
            continue

        context[map_dest] = context[map_source]


def slice(index, template):
    """Slice a template based on it's positional argument

    Arguments:
        index (int): Position at which to slice
        template (str): Template to slice

    Example:
        >>> slice(0, "{cwd}/{0}/assets/{1}/{2}")
        '{cwd}/{0}'
        >>> slice(1, "{cwd}/{0}/assets/{1}/{2}")
        '{cwd}/{0}/assets/{1}'

    """

    try:
        return re.match("^.*{[%i]}" % index, template).group()
    except AttributeError:
        raise ValueError("Index %i not found in template: %s"
                         % (index, template))
