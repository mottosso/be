"""be - Minimal Asset Management System

Usage:
    $ be project/item/type

Errors:
    PROJECT ERROR: Project has been misconfigured
    TEMPLATE ERROR: A template has been misconfigured

"""

import os
import sys
import subprocess

import _format
import _extern

from vendor import click

self = type("Scope", (object,), {})()
self.root = os.getcwd()
self.isactive = lambda: True if os.environ.get("BE_ACTIVE") else False


@click.group()
def main():
    r"""be - Minimal Asset Management System

    be initialises a context-sensitive environment for
    your project. Use "new" to start a new project, followed
    by "in" to enter it. A directory structure will have been
    setup for you in accordance with a project-specific file
    "templates.yaml" for any particular item you request,
    e.g. "peter".

    See help for each subcommand for more information and
    http://github.com/abstractfactory/be/wiki for documentation.

    \b
    Usage:
        # List available projects
        $ be ls
        - hulk
        # Start new project
        $ be new spiderman
        "spiderman" created.
        # Enter project
        $ be in spiderman/peter/model
        # Print environment
        $ be dump
        BE_PROJECT=spiderman
        BE_ITEM=peter
        BE_TYPE=model

    \b
    Environment:
        BE_PROJECT (str): Name of current project
        BE_ITEM (str): Name of current item
        BE_TYPE (str): Family of current item
        BE_DEVELOPMENTDIR (str): Absolute path to current development directory
        BE_PROJECTROOT (str): Absolute path to current project
        BE_PROJECTSROOT (str): Absolute path to where projects are located
        BE_ACTIVE (bool): In an active environment

    """


@click.command(name="in")
@click.argument("context")
def in_(context):
    """Set the current context to `context`

    \b
    Usage:
        $ be in project/item/type

    """

    try:
        project, item, type = str(context).split("/")
    except:
        sys.stderr.write("Invalid syntax, the format is project/item/type")
        sys.exit(1)

    project_dir = _format.project_dir(self.root, project)
    if not os.path.exists(project_dir):
        sys.stderr.write("Project \"%s\" not found. " % project)
        sys.exit(1)

    templates = _extern.load_templates(project)
    inventory = _extern.load_inventory(project)

    development_dir = _format.development_directory(
        templates, inventory, project, item, type)
    if not os.path.exists(development_dir):
        sys.stdout.write("No development directory found. Create? [Y/n]: ")
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
        BE_ACTIVE="true",
        BE_PROJECTSROOT=self.root,
        BE_PROJECTROOT=os.path.join(self.root, project),
        BE_DEVELOPMENTDIR=development_dir,
        BE_PROJECT=project,
        BE_ITEM=item,
        BE_TYPE=type)
    ))


@click.command()
@click.argument("name")
def new(name):
    """Create new default project

    \b
    Usage:
        $ be new spiderman
        "spiderman" created

    """

    if self.isactive():
        click.echo("Please exit current project before starting a new")
        sys.exit(1)

    new_dir = os.path.join(self.root, name)

    if not os.path.exists(new_dir):
        _extern.create_new(new_dir)
    else:
        sys.stderr.write("\"%s\" already exists" % name)
        sys.exit(1)

    sys.stdout.write("\"%s\" created" % name)


@click.command()
def ls():
    """List contents of current context

    \b
    Usage:
        $ be ls
        - peter
        - maryjane

    """

    for project in os.listdir(self.root):
        abspath = os.path.join(self.root, project)
        if not os.path.isdir(abspath):
            continue
        click.echo("- %s" % project)


@click.command()
def dump():
    """Print current environment

    \b
    Usage:
        $ be dump
        BE_PROJECT=spiderman
        BE_ITEM=peter
        BE_TYPE=model
        ...

    """

    if not self.isactive():
        click.echo("No environment")
    else:
        for key in ("BE_PROJECT",
                    "BE_ITEM",
                    "BE_TYPE"
                    "BE_DEVELOPMENTDIR",
                    "BE_PROJECTROOT",
                    "BE_PROJECTSROOT"):
            click.echo("%s=%s" % (key, os.environ.get(key)))


main.add_command(in_)
main.add_command(new)
main.add_command(ls)
main.add_command(dump)


if __name__ == '__main__':
    main()
