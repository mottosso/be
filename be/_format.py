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
        template_key = template_key_from_args(settings, topics)
    except IndexError as exc:
            lib.echo("At least %s topics are required" % str(exc))
            sys.exit(lib.USER_ERROR)

    replacement_fields = replacement_fields_from_environment(environment)
    template = template_from_item(inventory, template_key)
    pattern = pattern_from_template(templates, template)

    positional_arguments = find_positional_arguments(pattern)
    highest_argument = find_highest_position(positional_arguments)
    highest_available = len(topics) - 1
    if highest_available < highest_argument:
        lib.echo("Template for \"%s\" requires at least %i arguments" % (
            template_key, highest_argument + 1))
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


def template_key_from_args(settings, topics):
    """Map key from settings to key in topic

    Example:
        key: {0} -> be in hello world == hello
        key: {1} -> be in hello world == world

    Raises:
        IndexError (int): With number of required arguments
            for the project

    """

    key = settings.get("templates", {}).get("key", "{1}")
    if re.match("{\d+}", key):
        pos = int(key.strip("{}"))
        try:
            template_key = topics[pos]
        except IndexError:
            raise IndexError(pos + 1)

    else:
        lib.echo("be.yaml template key not recognised")
        sys.exit(lib.PROJECT_ERROR)

    return template_key


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
                print("Warning: Duplicate template found "
                      "for \"%s:%s\"" % (template, item))
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



if __name__ == "__main__":
    inventory = {
        "character": ["ben", "jerry"],
        "prop": ["table"],
        "shot": [1000, 2000]
    }
    print items_from_inventory(inventory)
