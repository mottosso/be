"""be - Minimal Asset Management System

Usage:
    $ be project/item/type

Errors:
    PROJECT ERROR: Project has been misconfigured
    TEMPLATE ERROR: A template has been misconfigured

"""

import os
import sys
import time
import subprocess

import _format
import _extern
import lib

from vendor import click

self = type("Scope", (object,), {})()
self.home = os.path.dirname(__file__)
self.root = lambda: os.getcwd().replace("\\", "/")
self.isactive = lambda: "BE_ACTIVE" in os.environ


@click.group()
def main():
    """be - Minimal Asset Management System

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
        PROJECT=spiderman
        ITEM=peter
        TYPE=model

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


@click.command()
@click.argument("context")
@click.option("-y", "--yes", is_flag=True,
              help="Automatically accept any questions")
def in_(context, yes):
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

    project_dir = _format.project_dir(self.root(), project)
    if not os.path.exists(project_dir):
        sys.stderr.write("Project \"%s\" not found. " % project)
        sys.exit(1)

    templates = _extern.load_templates(project)
    inventory = _extern.load_inventory(project)

    development_dir = _format.development_directory(
        templates, inventory, project, item, type)
    if not os.path.exists(development_dir):
        create = False
        if yes:
            create = True
        else:
            sys.stdout.write("No development directory found. Create? [Y/n]: ")
            if raw_input().lower() in ("", "y", "yes"):
                create = True
        if create:
            os.makedirs(development_dir)
        else:
            sys.stdout.write("Cancelled")
            sys.exit(0)

    dirname = os.path.dirname(__file__)
    if os.name == "nt":
        shell = os.path.join(dirname, "_shell.bat")
    else:
        shell = os.path.join(dirname, "_shell.sh")

    env = {
        "BE_PROJECT": project,
        "BE_ITEM": item,
        "BE_TYPE": type,
        "BE_DEVELOPMENTDIR": development_dir,
        "BE_PROJECTROOT": os.path.join(
            self.root(), project).replace("\\", "/"),
        "BE_PROJECTSROOT": self.root(),
        "BE_ACTIVE": "true",
    }

    if "BE_TESTING" in os.environ:
        os.chdir(development_dir)
        os.environ.update(env)
        return

    sys.exit(subprocess.call(shell, shell=True,
             env=dict(os.environ, **env)))


def echo(text, silent=False, newline=True):
    if silent:
        return
    click.echo(text) if newline else sys.stdout.write(text)


@click.command()
@click.argument("preset")
@click.option("--name", default="blue_unicorn")
@click.option("--silent", is_flag=True)
def new(preset, name, silent):
    """Create new default preset

    \b
    Usage:
        $ be new ad
        "blue_unicorn" created
        $ be new film --name spiderman
        "spiderman" created

    """

    if self.isactive():
        echo("Please exit current preset before starting a new")
        sys.exit(1)

    new_dir = _format.project_dir(self.root(), name)
    if os.path.exists(new_dir):
        sys.stderr.write("\"%s\" already exists" % name)
        sys.exit(1)

    presets = _extern.local_presets()
    presets_dir = _extern.presets_dir()
    preset_dir = os.path.join(presets_dir, preset)

    try:
        if preset in presets:
            _extern.copy_preset(preset_dir, new_dir)

        else:
            echo("Finding preset for \"%s\".. " % preset, silent)
            time.sleep(1 if silent else 0)
            presets = _extern.github_presets()

            if preset not in presets:
                sys.stdout.write("\"%s\" not found" % preset)
                sys.exit(1)

            time.sleep(1 if silent else 0)
            repository = presets[preset]
            
            echo("Pulling %s.. " % repository, silent)
            try:
                _extern.pull_preset(repository, preset_dir)
            except IOError as e:
                echo(e)
                sys.exit(1)

            _extern.copy_preset(preset_dir, new_dir)

    except IOError:
        echo("ERROR: Could not write, do you have permission?")
        sys.exit(1)

    echo("\"%s\" created" % name, silent, newline=False)


@click.command()
def ls():
    """List contents of current context

    \b
    Usage:
        $ be ls
        - peter
        - maryjane

    """

    projects = list()
    for project in os.listdir(self.root()):
        abspath = os.path.join(self.root(), project)
        if not lib.isproject(abspath):
            continue
        projects.append(project)

    if not projects:
        click.echo("Empty")
        sys.exit(0)

    for project in projects:
        click.echo("- %s" % project)
    sys.exit(0)


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
        sys.stdout.write("No environment")
        sys.exit(1)

    for key, value in sorted(os.environ.iteritems()):
        if not key.startswith("BE_"):
            continue
        click.echo("%s=%s" % (key[3:], os.environ.get(key)))
    sys.exit(0)


@click.command()
def what():
    """Print current context"""
    if not self.isactive():
        sys.stdout.write("No environment")
        sys.exit(1)

    sys.stdout.write("{}/{}/{}".format(*(
        os.environ.get(k, "")
        for k in ("BE_PROJECT", "BE_ITEM", "BE_TYPE"))))


main.add_command(in_, name="in")
main.add_command(new)
main.add_command(ls)
main.add_command(dump)
main.add_command(what)
main.add_command(what, name="?")


if __name__ == '__main__':
    main()
