import os
import re
import sys

from vendor import yaml

_cache = dict()

default_templates = {
    "asset": "{cwd}/{project}/assets/{item}/{type}",
    "shot": "{cwd}/{project}/shots/{item}/{type}"
}

defaults_inventory = {
    "asset": ["peter", "maryjane"],
    "shot": [1000, 2000]
}


def create_new(new_dir):
    os.makedirs(new_dir)

    with open(os.path.join(new_dir, "templates.yaml"), "w") as f:
        yaml.dump(default_templates, f, default_flow_style=False)

    with open(os.path.join(new_dir, "inventory.yaml"), "w") as f:
        yaml.dump(defaults_inventory, f, default_flow_style=False)


def load_templates(project):
    """Return templates given name of project

    Arguments:
        project (str): Name of project

    """

    return resolve_references(load(project, "templates"))


def load_inventory(project):
    """Return available inventory from cwd

    Arguments:
        project (str): Name of project

    """

    return load(project, "inventory")


def load_be(project):
    return load(project, "be")


def load(project, fname):
    if fname not in _cache:
        path = os.path.join(os.getcwd(), project, "%s.yaml" % fname)
        try:
            with open(path) as f:
                _cache[fname] = yaml.load(f) or dict()
        except IOError:
            sys.stderr.write("PROJECT ERROR: %s.yaml not "
                             "defined for project \"%s\"" % (fname, project))
            sys.exit(1)

    return _cache[fname]


def resolve_references(templates):
    """Resolve {@} occurences by expansion

    Given a dictionary {"a": "{@b}/x", "b": "{key}/y"}
    Return {"a", "{key}/y/x", "b": "{key}/y"}

    {
        key: {@reference}/{variable} # pattern
    }

    In plain english, it looks within `pattern` for
    references and replaces them with the value of the
    matching key.

    {
        root: {cwd}/{project}
        item: {@root}/{item}
    }

    In the above case, `item` is referencing `root` which
    is resolved into this.

    {
        item: {cwd}/{project}/{item}
    }

    Example:
        >>> templates = {"a": "{@b}/x", "b": "{key}/y"}
        >>> resolved = _resolve_references(templates)
        >>> assert resolved["a"] == "{key}/y/x"

    """

    def repl(match):
        key = pattern[match.start():match.end()].strip("@{}")
        if key not in templates:
            sys.stderr.write("Unresolvable reference: \"%s\"" % key)
            sys.exit(1)
        return templates[key]

    for key, pattern in templates.copy().iteritems():
        templates[key] = re.sub("{@\w+}", repl, pattern)

    return templates


def test_template():
    os.chdir("../demo")
    print load_templates("thedeal")
