"""be - Minimal Asset Management System

Usage:
    $ be project/item/task

Return codes:
    0: No error
    1: Program fault  # returned from exceptions
    2: User error
    3: Project has been misconfigured
    4: A template has been misconfigured

"""

import os
import re
import sys
import time
import getpass
import tempfile
import subprocess

import _format
import _extern
import lib

from version import version
from vendor import click

self = type("Scope", (object,), {})()
self.isactive = lambda: "BE_ACTIVE" in os.environ
self.verbose = False

FIXED = 1 << 0
POSITIONAL = 1 << 1


@click.group()
@click.option("-v", "--verbose", is_flag=True)
def main(verbose):
    """be {0} - Minimal Directory and Environment Management System

    be initialises a context-sensitive environment for
    your project. Use "new" to start a new project, followed
    by "in" to enter it. A directory structure will have been
    setup for you in accordance with a project-specific file
    "templates.yaml" for any particular item you request,
    e.g. "peter".

    See help for each subcommand for more information and
    http://github.com/mottosso/be/wiki for documentation.

    \b
    Usage:
        $ be new ad --name spiderman
        "spiderman" created.
        $ be ls
        - spiderman
        $ be in spiderman shot1 animation
        $ be dump
        BE_PROJECT=spiderman
        BE_ITEM=peter
        BE_TASK=model

    """

    self.verbose = verbose
    _extern.verbose = verbose

main.help = main.help.format(version)


@main.command(name="in")
@click.argument("topics", nargs=-1, required=True)
@click.option("-y", "--yes", is_flag=True,
              help="Automatically accept any questions")
@click.option("-a", "--as", "as_", default=getpass.getuser(),
              help="Enter project as a different user")
@click.option("-e", "--enter", is_flag=True,
              help="Change the current working "
                   "directory to development directory")
@click.pass_context
def in_(ctx, topics, yes, as_, enter):
    """Set the current topics to `topics`

    \b
    Usage:
        $ be in project topics

    """

    topics = map(str, topics)  # They enter as unicode

    if self.isactive():
        lib.echo("ERROR: Exit current project first")
        sys.exit(lib.USER_ERROR)

    if len(topics[0].split("/")) == 3:
        syntax = FIXED
        project = topics[0].split("/")[0]
    else:
        syntax = POSITIONAL
        project = topics[0]

    project_dir = _format.project_dir(_extern.cwd(), project)
    if not os.path.exists(project_dir):
        lib.echo("Project \"%s\" not found. " % project)
        lib.echo("\nAvailable:")
        ctx.invoke(ls)
        sys.exit(lib.USER_ERROR)

    # Boot up
    settings = _extern.load_settings(project)
    templates = _extern.load_templates(project)
    inventory = _extern.load_inventory(project)
    environment = _extern.load_environment(project)
    environment.update({
        "BE_PROJECT": project,
        "BE_ALIASDIR": "",
        "BE_CWD": _extern.cwd(),
        "BE_CD": "",
        "BE_ROOT": "",
        "BE_TOPIC": " ".join(topics),  # e.g. shot1 anim
        "BE_DEVELOPMENTDIR": "",
        "BE_PROJECTROOT": os.path.join(
            _extern.cwd(), project).replace("\\", "/"),
        "BE_PROJECTSROOT": _extern.cwd(),
        "BE_ACTIVE": "True",
        "BE_USER": str(as_),
        "BE_SCRIPT": "",
        "BE_PYTHON": "",
        "BE_ENTER": "1" if enter else "",
        "BE_TEMPDIR": "",
        "BE_PRESETSDIR": "",
        "BE_GITHUB_API_TOKEN": ""
    })
    environment.update(os.environ)

    # Determine syntax
    if syntax & POSITIONAL:
        development_dir = _format.new_development_directory(
            settings, templates, inventory, environment, topics, as_)
    else:  # FIXED syntax
        development_dir = _format.development_directory(
            templates, inventory, topics, as_)

    environment["BE_DEVELOPMENTDIR"] = development_dir

    dirname = os.path.dirname(__file__)
    if os.name == "nt":
        shell = os.path.join(dirname, "_shell.bat")
    else:
        shell = os.path.join(dirname, "_shell.sh")

    tempdir = (tempfile.mkdtemp()
               if "BE_TEMPDIR" not in os.environ
               else os.environ["BE_TEMPDIR"])
    environment["BE_TEMPDIR"] = tempdir

    if enter and not os.path.exists(development_dir):
        create = False
        if yes:
            create = True
        else:
            sys.stdout.write("No development directory found. Create? [Y/n]: ")
            if raw_input().lower() in ("", "y", "yes"):
                create = True
        if create:
            ctx.invoke(mkdir, dir=development_dir)
        else:
            sys.stdout.write("Cancelled")
            sys.exit(lib.NORMAL)

    # Parse be.yaml
    if "script" in settings:
        environment["BE_SCRIPT"] = _extern.write_script(settings["script"], tempdir)

    if "python" in settings:
        script = "\n".join(settings["python"])
        environment["BE_PYTHON"] = script
        try:
            exec script in {"__name__": __name__}
        except Exception as e:
            lib.echo("ERROR: %s" % e)

    invalids = [v for v in environment.values() if not isinstance(v, str)]
    assert all(isinstance(v, str) for v in environment.values()), invalids

    # Create aliases
    cd_alias = ("cd %BE_DEVELOPMENTDIR%"
                if os.name == "nt" else "cd $BE_DEVELOPMENTDIR")

    aliases = settings.get("alias", {})
    aliases["home"] = cd_alias
    aliases_dir = _extern.write_aliases(aliases, tempdir)

    environment["PATH"] = aliases_dir + os.pathsep + environment.get("PATH", "")
    environment["BE_ALIASDIR"] = aliases_dir

    for map_source, map_dest in settings.get("redirect", {}).items():
        if re.match("{\d+}", map_source):
            topics_index = int(map_source.strip("{}"))
            topics_value = topics[topics_index]
            environment[map_dest] = topics_value
            continue

        environment[map_dest] = environment[map_source]

    if "BE_TESTING" in os.environ:
        os.chdir(development_dir)
        os.environ.update(environment)
        return

    try:
        sys.exit(subprocess.call(shell, shell=True, env=environment))
    finally:
        import shutil
        shutil.rmtree(tempdir)


@main.command()
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
        sys.exit(lib.USER_ERROR)

    if not name:
        count = 0
        name = lib.random_name()
        while name in _extern.projects():
            if count > 10:
                lib.echo("ERROR: Couldn't come up with a unique name :(")
                sys.exit(lib.USER_ERROR)
            name = lib.random_name()
            count += 1

    project_dir = _format.project_dir(_extern.cwd(), name)
    if os.path.exists(project_dir):
        lib.echo("\"%s\" already exists" % name)
        sys.exit(lib.USER_ERROR)

    presets_dir = _extern.presets_dir()
    preset_dir = os.path.join(presets_dir, preset)

    try:
        if not update and preset in _extern.local_presets():
            _extern.copy_preset(preset_dir, project_dir)

        else:
            lib.echo("Finding preset for \"%s\".. " % preset, silent)
            time.sleep(1 if silent else 0)

            if "/" not in preset:
                # Preset is relative, look it up from the Hub
                presets = _extern.github_presets()

                if preset not in presets:
                    sys.stdout.write("\"%s\" not found" % preset)
                    sys.exit(lib.USER_ERROR)

                time.sleep(1 if silent else 0)
                repository = presets[preset]

            else:
                # Absolute paths are pulled directly
                repository = preset

            repository = _extern.fetch_release(repository)
            lib.echo("Pulling %s.. " % repository, silent)

            # Remove existing preset
            if preset in _extern.local_presets():
                _extern.remove_preset(preset)

            try:
                _extern.pull_preset(repository, preset_dir)
            except IOError as e:
                lib.echo("ERROR: Sorry, something went wrong. Use --verbose for more")
                lib.echo(e)
                sys.exit(lib.USER_ERROR)

            _extern.copy_preset(preset_dir, project_dir)

    except IOError as exc:
        if self.verbose:
            lib.echo("ERROR: %s" % exc)
        else:
            lib.echo("ERROR: Could not write, do you have permission?")
        sys.exit(lib.PROGRAM_ERROR)

    lib.echo("\"%s\" created" % name, silent)


@main.command()
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

    if self.isactive():
        lib.echo("ERROR: Exit current project first")
        sys.exit(lib.USER_ERROR)

    presets = _extern.github_presets()

    if preset not in presets:
        sys.stdout.write("\"%s\" not found" % preset)
        sys.exit(lib.USER_ERROR)

    lib.echo("Are you sure you want to update \"%s\", "
             "any changes will be lost?: [y/N]: ", newline=False)
    if raw_input().lower() in ("y", "yes"):
        presets_dir = _extern.presets_dir()
        preset_dir = os.path.join(presets_dir, preset)

        repository = presets[preset]

        if clean:
            try:
                _extern.remove_preset(preset)
            except:
                lib.echo("ERROR: Could not clean existing preset")
                sys.exit(lib.USER_ERROR)

        lib.echo("Updating %s.. " % repository)

        try:
            _extern.pull_preset(repository, preset_dir)
        except IOError as e:
            lib.echo(e)
            sys.exit(lib.USER_ERROR)

    else:
        lib.echo("Cancelled")


@main.command()
def ls():
    """List contents of current context

    \b
    Usage:
        $ be ls
        - peter
        - maryjane

    """

    if self.isactive():
        lib.echo("ERROR: Exit current project first")
        sys.exit(lib.USER_ERROR)

    projects = list()
    for project in os.listdir(_extern.cwd()):
        abspath = os.path.join(_extern.cwd(), project)
        if not lib.isproject(abspath):
            continue
        projects.append(project)

    if not projects:
        lib.echo("Empty")
        sys.exit(lib.NORMAL)

    for project in sorted(projects):
        lib.echo("- %s" % project)
    sys.exit(lib.NORMAL)


@main.command()
@click.argument("dir", default=os.environ.get("BE_DEVELOPMENTDIR"))
@click.option("-e", "--enter", is_flag=True)
def mkdir(dir, enter):
    """Create directory with template for topic of the current environment

    """

    if not os.path.exists(dir):
        os.makedirs(dir)


@click.group()
def preset():
    """Create, manipulate and query presets"""


@preset.command(name="ls")
@click.option("--remote", is_flag=True, help="List remote presets")
def preset_ls(remote):
    """List presets

    \b
    Usage:
        $ be preset ls
        - ad
        - game
        - film

    """

    if self.isactive():
        lib.echo("ERROR: Exit current project first")
        sys.exit(lib.USER_ERROR)

    if remote:
        presets = _extern.github_presets()
    else:
        presets = _extern.local_presets()

    if not presets:
        lib.echo("No presets found")
        sys.exit(lib.NORMAL)
    for preset in sorted(presets):
        lib.echo("- %s" % preset)
    sys.exit(lib.NORMAL)


@preset.command(name="find")
@click.argument("query")
def preset_find(query):
    """Find preset from hub

    \b
    $ be find mypreset
    https://github.com/mottosso/be-mypreset.git

    """

    if self.isactive():
        lib.echo("ERROR: Exit current project first")
        sys.exit(lib.USER_ERROR)

    found = _extern.github_presets().get(query)
    if found:
        lib.echo(found)
    else:
        lib.echo("Unable to locate preset \"%s\"" % query)


@main.command()
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
        lib.echo("ERROR: Enter a project first")
        sys.exit(lib.USER_ERROR)

    for key in sorted(os.environ):
        if not key.startswith("BE_"):
            continue
        lib.echo("%s=%s" % (key, os.environ.get(key)))

    project = os.environ["BE_PROJECT"]
    root = os.environ["BE_PROJECTSROOT"]
    settings = _extern.load(project, "be", optional=True, root=root)
    environ = settings.get("redirect", {}).items()
    for map_source, map_dest in sorted(environ):
        lib.echo("%s=%s" % (map_dest, os.environ.get(map_dest)))

    sys.exit(lib.NORMAL)


@main.command(name="?")
def what():
    """Print current context"""

    if not self.isactive():
        lib.echo("No topic")
        sys.exit(lib.USER_ERROR)

    lib.echo(os.environ.get("BE_TOPIC", "This is a bug"))


if __name__ == '__main__':
    main()
