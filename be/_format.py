import os
import re
import sys

import lib


def pos_development_directory(settings,
                              templates,
                              inventory,
                              environment,
                              topics,
                              user):
    """Return absolute path to development directory

    Arguments:
        settings (dict): be.yaml
        templates (dict): templates.yaml
        inventory (dict): inventory.yaml
        topics (list): Arguments to `in`
        user (str): Current `be` user

    """

    try:
        key = settings.get("templates", {}).get("key") or "{1}"
        template_binding = binding_from_topics(key, topics)
    except IndexError as exc:
            lib.echo("At least %s topics are required" % str(exc))
            sys.exit(lib.USER_ERROR)

    replacement_fields = replacement_fields_from_environment(environment)
    template = template_from_item(inventory, template_binding)
    pattern = pattern_from_template(templates, template)

    positional_arguments = find_positional_arguments(pattern)
    highest_argument = find_highest_position(positional_arguments)
    highest_available = len(topics) - 1
    if highest_available < highest_argument:
        lib.echo("Template for \"%s\" requires at least %i arguments" % (
            template_binding, highest_argument + 1))
        sys.exit(lib.USER_ERROR)

    try:
        return pattern.format(*topics, **replacement_fields).replace("\\", "/")
    except KeyError as exc:
        lib.echo("TEMPLATE ERROR: %s is not an available key\n" % exc)
        lib.echo("Available tokens:")
        for key in replacement_fields:
            lib.echo("\n- %s" % key)
        sys.exit(lib.TEMPLATE_ERROR)


def fixed_development_directory(templates, inventory, topics, user):
    """Return absolute path to development directory

    Arguments:
        project (str): Name of project
        item (str): Name of item within project
        task (str): Family of item

    """

    lib.echo("Fixed syntax has been deprecated, see positional syntax")

    project, item, task = topics[0].split("/")

    template = template_from_item(inventory, item)
    pattern = pattern_from_template(templates, template)

    if find_positional_arguments(pattern):
        lib.echo("\"%s\" uses a positional syntax" % project)
        lib.echo("Try this:")
        lib.echo("  be in %s" % " ".join([project, item, task]))
        sys.exit(lib.USER_ERROR)

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
        lib.echo("TEMPLATE ERROR: %s is not an available key\n" % exc)
        lib.echo("Available keys")
        for key in keys:
            lib.echo("\n- %s" % key)
        sys.exit(1)


def replacement_fields_from_environment(environment):
    """Convert be environment variables to replacement fields

    Example:
        BE_KEY=value -> {"key": "value}

    Arguments:
        environment (dict): The `be` environment

    """

    return dict((k[3:].lower(), environment[k])
                for k in environment if k.startswith("BE_"))


def binding_from_topics(key, topics):
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
        lib.echo("be.yaml template key not recognised")
        sys.exit(lib.PROJECT_ERROR)

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
        lib.echo("No template named \"%s\"" % name)
        sys.exit(1)

    return templates[name]


def items_from_inventory(inventory):
    items_ = list()
    for template, items in inventory.iteritems():
        for item in items:
            if item in items_:
                lib.echo("Warning: Duplicate item found, "
                         "for \"%s\"" % item)
                continue
            items_.append(item)
    return items_


def template_from_item(inventory, item):
    """Return template name for `item`

    Arguments:
        project: Name of project
        item (str): Name of item

    """

    templates = dict()
    for template, items_ in inventory.iteritems():
        for item_ in items_:
            if isinstance(item_, dict):
                item_ = item_.keys()[0]
            item_ = str(item_)  # Key may be number
            if item_ in templates:
                print("Warning: Duplicate item found "
                      "for \"%s: %s\"" % (template, item_))
            templates[item_] = template

    try:
        return templates[item]

    except KeyError:
        lib.echo("\"%s\" not found" % item)
        if templates:
            lib.echo("\nAvailable:")
            for item_ in sorted(templates, key=lambda a: (templates[a], a)):
                lib.echo("- %s (%s)" % (item_, templates[item_]))
        sys.exit(1)


def parse_environment(fields, environment, topics):
    """Resolve the be.yaml environment key

    Features:
        - Lists, e.g. ["/path1", "/path2"]
        - Environment variable references, via $
        - Replacement field references, e.g. {key}
        - Topic eferences, e.g. {1}

    """

    fields = _resolve_environment_lists(fields)
    fields = _resolve_environment_references(fields, environment)
    fields = _resolve_environment_fields(fields, environment, topics)
    return fields


def _resolve_environment_lists(environment):
    """Concatenate environment lists"""
    for key, value in environment.copy().iteritems():
        if isinstance(value, list):
            environment[key] = os.pathsep.join(value)
    return environment


def _resolve_environment_references(fields, environment):
    """Resolve $ occurences by expansion

    Given a dictionary {"PATH": "$PATH;somevalue;{0}"}
    Return {"PATH": "value_of_PATH;somevalue;myproject"},
    given that the first topic - {0} - is "myproject"

    Arguments:
        fields (dict): Environment from be.yaml
        environment (dict): Source environment

    """

    # Resolve references
    def repl(match):
        key = pattern[match.start():match.end()].strip("$")
        if key not in environment:
            sys.stderr.write("ERROR: Unavailable "
                             "fields variable: \"%s\"" % key)
            sys.exit(lib.USER_ERROR)
        return environment[key]

    pat = re.compile("\$\w+", re.IGNORECASE)
    for key, pattern in fields.copy().iteritems():
        fields[key] = pat.sub(repl, pattern)

    return fields


def _resolve_environment_fields(fields, environment, topics):
    """Resolve {} occurences

    Supports both positional and BE_-prefixed variables.

    Example:
        BE_MYKEY -> "{myvalue}" from `BE_MYKEY`
        {1} -> "{mytask}" from `be in myproject mytask`

    Returns:
        Dictionary of resolved fields

    """

    source_dict = replacement_fields_from_environment(environment)
    source_dict.update(dict((str(topics.index(topic)), topic)
                            for topic in topics))

    def repl(match):
        key = pattern[match.start():match.end()].strip("{}")
        try:
            return source_dict[key]
        except KeyError:
            lib.echo("PROJECT ERROR: Unavailable reference \"%s\" "
                     "in be.yaml" % key)
            sys.exit(lib.PROJECT_ERROR)

    for key, pattern in fields.copy().iteritems():
        fields[key] = re.sub("{[\d\w]+}", repl, pattern)

    return fields
