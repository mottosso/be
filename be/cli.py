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
@click.pass_context
def in_(ctx, context, yes):
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
        lib.echo("Project \"%s\" not found. " % project)
        lib.echo("\nAvailable:")
        ctx.invoke(ls)
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


@click.command()
@click.argument("preset")
@click.option("--name", help="Name of your new project")
@click.option("--silent", is_flag=True,
              help="Print only errors")
@click.option("--update", "-U", is_flag=True,
              help="Update preset to latest version before creating")
def new(preset, name, silent, update):
    """Create new default preset

    \b
    Usage:
        $ be new ad
        "blue_unicorn" created
        $ be new film --name spiderman
        "spiderman" created

    """

    if self.isactive():
        lib.echo("Please exit current preset before starting a new")
        sys.exit(1)

    if not name:
        name = lib.random_name()

    new_dir = _format.project_dir(self.root(), name)
    if os.path.exists(new_dir):
        lib.echo("\"%s\" already exists" % name)
        sys.exit(1)

    presets_dir = _extern.presets_dir()
    preset_dir = os.path.join(presets_dir, preset)

    try:
        if not update and preset in _extern.local_presets():
            _extern.copy_preset(preset_dir, new_dir)

        else:
            lib.echo("Finding preset for \"%s\".. " % preset, silent)
            time.sleep(1 if silent else 0)
            presets = _extern.github_presets()

            if preset not in presets:
                sys.stdout.write("\"%s\" not found" % preset)
                sys.exit(1)

            time.sleep(1 if silent else 0)
            repository = presets[preset]

            lib.echo("Pulling %s.. " % repository, silent)
            try:
                _extern.pull_preset(repository, preset_dir)
            except IOError as e:
                lib.echo(e)
                sys.exit(1)

            _extern.copy_preset(preset_dir, new_dir)

    except IOError:
        lib.echo("ERROR: Could not write, do you have permission?")
        sys.exit(1)

    lib.echo("\"%s\" created" % name, silent)


@click.command()
@click.argument("preset")
@click.option("--clean", is_flag=True)
def update(preset, clean):
    """Update a local preset

    This command will cause `be` to pull a preset already
    available locally.

    \b
    Usage:
        $ be update ad
        Updating "ad"..

    """

    presets = _extern.github_presets()

    if preset not in presets:
        sys.stdout.write("\"%s\" not found" % preset)
        sys.exit(1)

    lib.echo("Are you sure you want to update \"%s\", "
             "any changes will be lost?: [y/N]: ", newline=False)
    if raw_input().lower() in ("y", "yes"):
        presets_dir = _extern.presets_dir()
        preset_dir = os.path.join(presets_dir, preset)

        repository = presets[preset]

        if clean:
            try:
                _extern.remove_preset()
            except:
                lib.echo("Error: Could not clean existing preset")
                sys.exit(1)

        lib.echo("Updating %s.. " % repository)

        try:
            _extern.pull_preset(repository, preset_dir)
        except IOError as e:
            lib.echo(e)
            sys.exit(1)

    else:
        lib.echo("Cancelled")


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
        lib.echo("Empty")
        sys.exit(0)

    for project in projects:
        lib.echo("- %s" % project)
    sys.exit(0)


@click.group()
def preset():
    """Create, manipulate and query presets"""


@click.command()
@click.option("--remote", is_flag=True, help="List remote presets")
def preset_ls(remote):
    """List presets"""
    if remote:
        presets = _extern.github_presets()
    else:
        presets = _extern.local_presets()

    if not presets:
        lib.echo("No presets found")
        sys.exit(0)
    for preset in presets:
        lib.echo("- %s" % preset)
    sys.exit(0)


@click.command()
@click.argument("query")
def preset_find(query):
    """Find preset from hub

    \b
    $ be find mypreset
    https://github.com/mottosso/be-mypreset.git

    """

    found = _extern.github_presets().get(query)
    if found:
        lib.echo(found)
    else:
        lib.echo("Unable to locate preset \"%s\"" % query)


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
        lib.echo("%s=%s" % (key[3:], os.environ.get(key)))
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
main.add_command(update)
main.add_command(preset)
preset.add_command(preset_ls, name="ls")
preset.add_command(preset_find, name="find")


if __name__ == '__main__':
    main()
