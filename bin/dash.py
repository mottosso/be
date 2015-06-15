
import os
import re
import sys
import getpass
import argparse
import subprocess

from vendor import yaml

_cache = dict()


def cli():
    """Launch a subshell for context.

    Added environment variables:
        PROJECTSROOT: Absolute path to where projects are located
        PROJECTROOT: Absolute path to current project
        DEVELOPMENTDIR: Absolute path to current development directory
        PROJECT: Name of current project
        ASSET: Name of current asset
        FAMILY: Family of current asset

    Usage:
        $ dash thedeal/ben/rig

    """

    parser = argparse.ArgumentParser(description=cli.__doc__.split("\n")[0])
    parser.add_argument("context", type=str)
    
    context = parser.parse_args().context

    try:
        project, asset, family = context.split("/")
    except:
        sys.stdout.write("Invalid syntax, the format is project/asset/family")
        sys.exit(1)

    project_dir = _compute_project_dir(project)
    if not os.path.exists(project_dir):
        sys.stdout.write("Project \"%s\" not found. " % project)
        sys.exit(0)

    development_dir = _compute_development_directory(project, asset, family)
    if not os.path.exists(development_dir):
        sys.stdout.write("Create new development directory for %s? [Y/n]: " % context)
        if raw_input().lower() in ("", "y", "yes"):
            os.makedirs(development_dir)
        else:
            sys.stdout.write("Cancelled")
            sys.exit(0)

    dirname = os.path.dirname(__file__)
    if os.name == "nt":
        shell = os.path.join(dirname, "_shell.bat")
    else:
        shell = os.path.join(dirname, "_shell.sh")

    sys.exit(subprocess.call(shell, shell=True, env=dict(
        os.environ,
        PROJECTSROOT=os.getcwd(),
        PROJECTROOT=os.path.join(os.getcwd(), project),
        DEVELOPMENTDIR=development_dir,
        PROJECT=project,
        ASSET=asset,
        FAMILY=family)
    ))


def _load_schema(project):
    """Return schema given name of project

    Arguments:
        project (str): Name of project

    """

    if "schemas" not in _cache:
        path = os.path.join(os.getcwd(), project, "schemas.yaml")
        try:
            with open(path) as f:
                _cache["schemas"] = _resolve_references(yaml.load(f))
        except IOError:
            sys.stdout.write("Error: schemas.yaml not defined for project \"%s\"" % project)
            sys.exit(1)

    return _cache["schemas"]

def _load_inventory(project):
    """Return available inventory from cwd

    Arguments:
        project (str): Name of project

    """

    if "inventory" not in _cache:
        path = os.path.join(os.getcwd(), project, "inventory.yaml")
        try:
            with open(path) as f:
                _cache["inventory"] = yaml.load(f) or dict()
        except IOError:
            sys.stdout.write("inventory.yaml not defined for project \"%s\"" % project)
            sys.exit(1)

    return _cache["inventory"]


def _compute_project_dir(project):
    """Return absolute path to project given the name `project`

    ..note:: Assumed to root at the current working directory.

    Arguments:
        project (str): Name of project

    """

    return os.path.join(os.getcwd(), project)


def _pattern_from_template(project, template):
    """Return pattern for template

    Arguments:
        project: Name of project
        template (str): Name of template

    """

    schema = _load_schema(project)

    if not template in schema:
        sys.stdout.write("No template named \"%s\"" % template)
        sys.exit(1)

    return schema[template]


def _resolve_references(schema):
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
        asset: {@root}/{asset}
    }

    In the above case, `asset` is referencing `root` which
    is resolved into this.

    {
        asset: {cwd}/{project}/{asset}
    }

    # Example:
    #     >>> schema = {"a": "{@b}/x", "b": "{key}/y"}
    #     >>> resolved = _resolve_references(schema)
    #     >>> assert resolved["a"] == "{key}/y/x"

    """

    def repl(match):
        key = pattern[match.start():match.end()].strip("@{}")
        if not key in schema:
            sys.stdout.write("Unresolvable reference: \"%s\"" % key)
            sys.exit(1)
        return schema[key]

    for key, pattern in schema.copy().iteritems():
        schema[key] = re.sub("{@\w+}", repl, pattern)

    return schema


def _template_from_asset(project, asset):
    """Return template for `asset`

    Arguments:
        project: Name of project
        asset (str): Name of asset

    """

    inventory = _load_inventory(project)
    
    assets = dict()
    for template, assets_ in inventory.iteritems():
        for asset_ in assets_:
            asset_ = str(asset_) # Key may be number
            if isinstance(asset_, dict):
                asset_ = asset_.keys()[0]
            if asset_ in assets:
                print("Warning: Duplicate template found for \"%s:%s\"" % (template, asset))
            assets[asset_] = template

    try:
        return assets[asset]

    except KeyError:
        sys.stdout.write("\"%s\" not found" % asset)
        if assets:
            sys.stdout.write("\nAvailable:")
            for asset_ in sorted(assets, key=lambda a: assets[a]):
                sys.stdout.write("\n- %s|%s" % (assets[asset_], asset_))
        sys.exit(1)


def _compute_development_directory(project, asset, family):
    """Return absolute path to development directory

    Arguments:
        project (str): Name of project
        asset (str): Name of asset within project
        family (str): Family of asset

    """

    template = _template_from_asset(project, asset)
    pattern = _pattern_from_template(project, template)

    return pattern.format(**{
        "cwd": os.getcwd(),
        "project": project,
        "asset": asset,
        "user": getpass.getuser(),
        "family": family
    }).replace("\\", "/")


# def test_cdd():
#     os.chdir("../test")
#     _compute_development_directory("thedeal", "ben", "rig")
    

if __name__ == '__main__':
    # import doctest
    # doctest.testmod()
    cli()
