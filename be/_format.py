import os
import sys
import getpass


def development_directory(templates, inventory, project, item, type):
    """Return absolute path to development directory

    Arguments:
        project (str): Name of project
        item (str): Name of item within project
        type (str): Family of item

    """

    template = template_from_item(inventory, project, item)
    pattern = pattern_from_template(templates, project, template)

    keys = {
        "cwd": os.getcwd(),
        "project": project,
        "item": item,
        "user": getpass.getuser(),
        "type": type
    }

    try:
        return pattern.format(**keys).replace("\\", "/")
    except KeyError as exc:
        sys.stderr.write("TEMPLATE ERROR: %s is not an available key\n" % exc)
        sys.stderr.write("Available keys")
        for key in keys:
            sys.stderr.write("\n- %s" % key)
        sys.exit(1)


def project_dir(root, project):
    """Return absolute path to project given the name `project`

    ..note:: Assumed to root at the current working directory.

    Arguments:
        project (str): Name of project

    """

    return os.path.join(root, project)


def pattern_from_template(templates, project, name):
    """Return pattern for name

    Arguments:
        project: Name of project
        name (str): Name of name

    """

    if name not in templates:
        sys.stderr.write("No template named \"%s\"" % name)
        sys.exit(1)

    return templates[name]


def template_from_item(inventory, project, item):
    """Return template name for `item`

    Arguments:
        project: Name of project
        item (str): Name of item

    """

    items = dict()
    for template, items_ in inventory.iteritems():
        for item_ in items_:
            if isinstance(item_, dict):
                item_ = item_.keys()[0]
            item_ = str(item_)  # Key may be number
            if item_ in items:
                print("Warning: Duplicate template found "
                      "for \"%s:%s\"" % (template, item))
            items[item_] = template

    try:
        return items[item]

    except KeyError:
        sys.stderr.write("\"%s\" not found" % item)
        if items:
            sys.stderr.write("\nAvailable:")
            for item_ in sorted(items, key=lambda a: (items[a], a)):
                sys.stderr.write("\n- %s|%s" % (items[item_], item_))
        sys.exit(1)


def test_cdd():
    os.chdir("../demo")
    development_directory("thedeal", "ben", "rig")
