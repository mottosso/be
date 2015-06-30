import os
import re
import sys

import lib

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
        topics (list): Arguments to `in`
        user (str): Current `be` user

    """

    replacement_fields = replacement_fields_from_context(context)
    binding = binding_from_item(inventory, item)
    pattern = pattern_from_template(templates, binding)

    positional_arguments = find_positional_arguments(pattern)
    highest_argument = find_highest_position(positional_arguments)
    highest_available = len(topics) - 1
    if highest_available < highest_argument:
        lib.echo("Template for \"%s\" requires at least %i arguments" % (
            item, highest_argument + 1))
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

    template = binding_from_item(inventory, item)
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
                lib.echo("Warning: Duplicate item found, "
                         "for \"%s: %s\"" % (binding, item))
                continue
            inverted[item] = binding

    return inverted


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

    except KeyError:
        lib.echo("\"%s\" not found" % item)
        if bindings:
            lib.echo("\nAvailable:")
            for item_ in sorted(bindings, key=lambda a: (bindings[a], a)):
                lib.echo("- %s (%s)" % (item_, bindings[item_]))
        sys.exit(1)


def parse_environment(fields, context, topics):
    """Resolve the be.yaml environment key

    Features:
        - Lists, e.g. ["/path1", "/path2"]
        - Environment variable references, via $
        - Replacement field references, e.g. {key}
        - Topic eferences, e.g. {1}

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
                sys.exit(lib.USER_ERROR)
            return context[key]

        pat = re.compile("\$\w+", re.IGNORECASE)
        for key, pattern in fields.copy().iteritems():
            fields[key] = pat.sub(repl, pattern)

        return fields

    def _resolve_environment_fields(fields, context, topics):
        """Resolve {} occurences

        Supports both positional and BE_-prefixed variables.

        Example:
            BE_MYKEY -> "{myvalue}" from `BE_MYKEY`
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
                lib.echo("PROJECT ERROR: Unavailable reference \"%s\" "
                         "in be.yaml" % key)
                sys.exit(lib.PROJECT_ERROR)

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
