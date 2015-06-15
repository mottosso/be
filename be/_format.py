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

    template = template_from_item(inventory, item)
    pattern = pattern_from_template(templates, template)

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


def pattern_from_template(templates, name):
    """Return pattern for name

    Arguments:
        templates (dict): Current templates
        name (str): Name of name

    """

    if name not in templates:
        sys.stderr.write("No template named \"%s\"" % name)
        sys.exit(1)

    return templates[name]


def items_from_inventory(inventory):
    items_ = list()
    for template, items in inventory.iteritems():
        for item in items:
            if item in items_:
                sys.stderr.write("Warning: Duplicate item found "
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
        sys.stderr.write("\"%s\" not found" % item)
        if templates:
            sys.stderr.write("\nAvailable:")
            for item_ in sorted(templates, key=lambda a: (templates[a], a)):
                sys.stderr.write("\n- %s|%s" % (templates[item_], item_))
        sys.exit(1)


def test_cdd():
    os.chdir("../demo")
    development_directory("thedeal", "ben", "rig")


if __name__ == "__main__":
    inventory = {
        "character": ["ben", "jerry"],
        "prop": ["table"],
        "shot": [1000, 2000]
    }
    print items_from_inventory(inventory)
