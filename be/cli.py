"""be - Minimal Asset Management System

Usage:
    $ be project item task

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

from . import lib
from . import _extern

from . import version
from .vendor import click

self = type("Scope", (object,), {})()
self.isactive = lambda: "BE_ACTIVE" in os.environ
self.verbose = False


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
        $ pwd
        /projects/spiderman/film/shot1/animation

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

    Environment:
        BE_PROJECT: First topic
        BE_CWD: Current `be` working directory
        BE_TOPICS: Arguments to `in`
        BE_DEVELOPMENTDIR: Absolute path to current development directory
        BE_PROJECTROOT: Absolute path to current project
        BE_PROJECTSROOT: Absolute path to where projects are located
        BE_ACTIVE: 0 or 1, indicates an active be environment
        BE_USER: Current user, overridden with `--as`
        BE_SCRIPT: User-supplied shell script
        BE_PYTHON: User-supplied python script
        BE_ENTER: 0 or 1 depending on whether the topic was entered
        BE_GITHUB_API_TOKEN: Optional GitHub API token
        BE_ENVIRONMENT: Space-separated list of user-added
            environment variables
        BE_TEMPDIR: Directory in which temporary files are stored
        BE_PRESETSDIR: Directory in which presets are searched
        BE_ALIASDIR: Directory in which aliases are written
        BE_BINDING: Binding between template and item in inventory

    \b
    Usage:
        $ be in project topics

    """

    topics = map(str, topics)  # They enter as unicode

    if self.isactive():
        lib.echo("ERROR: Exit current project first")
        sys.exit(lib.USER_ERROR)

    # Determine topic syntax
    if len(topics[0].split("/")) == 3:
        topic_syntax = lib.FIXED
        project = topics[0].split("/")[0]
    else:
        topic_syntax = lib.POSITIONAL
        project = topics[0]

    project_dir = lib.project_dir(_extern.cwd(), project)
    if not os.path.exists(project_dir):
        lib.echo("Project \"%s\" not found. " % project)
        lib.echo("\nAvailable:")
        ctx.invoke(ls)
        sys.exit(lib.USER_ERROR)

    # Boot up
    context = lib.context(root=_extern.cwd(), project=project)

    be = _extern.load_be(project)
    templates = _extern.load_templates(project)
    inventory = _extern.load_inventory(project)
    context.update({
        "BE_PROJECT": project,
        "BE_USER": str(as_),
        "BE_ENTER": "1" if enter else "",
        "BE_TOPICS": " ".join(topics)
    })

    # Remap topic syntax, for backwards compatibility
    # In cases where the topic is entered in a way that
    # differs from the template, remap topic to template.
    if any(re.findall("{\d+}", pattern) for pattern in templates.values()):
        template_syntax = lib.POSITIONAL
    else:
        template_syntax = lib.FIXED

    if topic_syntax & lib.POSITIONAL and not template_syntax & lib.POSITIONAL:
        topics = ["/".join(topics)]
    if topic_syntax & lib.FIXED and not template_syntax & lib.FIXED:
        topics[:] = topics[0].split("/")

    try:
        key = be.get("templates", {}).get("key") or "{1}"
        item = lib.item_from_topics(key, topics)
        binding = lib.binding_from_item(inventory, item)
        context["BE_BINDING"] = binding
    except IndexError as exc:
        lib.echo("At least %s topics are required" % str(exc))
        sys.exit(lib.USER_ERROR)

    except KeyError as exc:
        lib.echo("\"%s\" not found" % item)
        if exc.bindings:
            lib.echo("\nAvailable:")
            for item_ in sorted(exc.bindings,
                                key=lambda a: (exc.bindings[a], a)):
                lib.echo("- %s (%s)" % (item_, exc.bindings[item_]))
        sys.exit(lib.USER_ERROR)

    # Finally, determine a development directory
    # based on the template-, not topic-syntax.
    if template_syntax & lib.POSITIONAL:
        try:
            development_dir = lib.pos_development_directory(
                templates=templates,
                inventory=inventory,
                context=context,
                topics=topics,
                user=as_,
                item=item)
        except KeyError as exc:
            lib.echo("\"%s\" not found" % item)
            if exc.bindings:
                lib.echo("\nAvailable:")
                for item_ in sorted(exc.bindings,
                                    key=lambda a: (exc.bindings[a], a)):
                    lib.echo("- %s (%s)" % (item_, exc.bindings[item_]))
            sys.exit(lib.USER_ERROR)

    else:  # FIXED topic_syntax
        development_dir = lib.fixed_development_directory(
            templates,
            inventory,
            topics,
            as_)

    context["BE_DEVELOPMENTDIR"] = development_dir

    tempdir = (tempfile.mkdtemp()
               if not os.environ.get("BE_TEMPDIR")
               else os.environ["BE_TEMPDIR"])
    context["BE_TEMPDIR"] = tempdir

    # Should it be entered?
    if enter and not os.path.exists(development_dir):
        create = False
        if yes:
            create = True
        else:
            sys.stdout.write("No development directory found. Create? [Y/n]: ")
            sys.stdout.flush()
            if raw_input().lower() in ("", "y", "yes"):
                create = True
        if create:
            ctx.invoke(mkdir, dir=development_dir)
        else:
            sys.stdout.write("Cancelled")
            sys.exit(lib.NORMAL)

    # Parse be.yaml
    if "script" in be:
        context["BE_SCRIPT"] = _extern.write_script(
            be["script"], tempdir).replace("\\", "/")

    if "python" in be:
        script = "\n".join(be["python"])
        context["BE_PYTHON"] = script
        try:
            exec script in {"__name__": __name__}
        except Exception as e:
            lib.echo("ERROR: %s" % e)

    invalids = [v for v in context.values() if not isinstance(v, str)]
    assert all(isinstance(v, str) for v in context.values()), invalids

    # Create aliases
    aliases_dir = _extern.write_aliases(
        be.get("alias", {}), tempdir)

    context["PATH"] = (aliases_dir
                       + os.pathsep
                       + context.get("PATH", ""))
    context["BE_ALIASDIR"] = aliases_dir

    # Parse redirects
    lib.parse_redirect(
        be.get("redirect", {}), topics, context)

    # Override inherited context
    # with that coming from be.yaml.
    if "environment" in be:
        parsed = lib.parse_environment(
            fields=be["environment"],
            context=context,
            topics=topics)
        context["BE_ENVIRONMENT"] = " ".join(parsed.keys())
        context.update(parsed)

    if "BE_TESTING" in context:
        os.chdir(development_dir)
        os.environ.update(context)
    else:
        parent = lib.parent()
        cmd = lib.cmd(parent)

        # Store reference to calling shell
        context["BE_SHELL"] = parent

        try:
            sys.exit(subprocess.call(cmd, env=context))
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

    project_dir = lib.project_dir(_extern.cwd(), name)
    if os.path.exists(project_dir):
        lib.echo("\"%s\" already exists" % name)
        sys.exit(lib.USER_ERROR)

    username, preset = ([None] + preset.split("/", 1))[-2:]
    presets_dir = _extern.presets_dir()
    preset_dir = os.path.join(presets_dir, preset)

    # Is the preset given referring to a repository directly?
    relative = False if username else True

    try:
        if not update and preset in _extern.local_presets():
            _extern.copy_preset(preset_dir, project_dir)

        else:
            lib.echo("Finding preset for \"%s\".. " % preset, silent)
            time.sleep(1 if silent else 0)

            if relative:
                # Preset is relative, look it up from the Hub
                presets = _extern.github_presets()

                if preset not in presets:
                    sys.stdout.write("\"%s\" not found" % preset)
                    sys.exit(lib.USER_ERROR)

                time.sleep(1 if silent else 0)
                repository = presets[preset]

            else:
                # Absolute paths are pulled directly
                repository = username + "/" + preset

            lib.echo("Pulling %s.. " % repository, silent)
            repository = _extern.fetch_release(repository)

            # Remove existing preset
            if preset in _extern.local_presets():
                _extern.remove_preset(preset)

            try:
                _extern.pull_preset(repository, preset_dir)
            except IOError as e:
                lib.echo("ERROR: Sorry, something went wrong.\n"
                         "Use be --verbose for more")
                lib.echo(e)
                sys.exit(lib.USER_ERROR)

            try:
                _extern.copy_preset(preset_dir, project_dir)
            finally:
                # Absolute paths are not stored locally
                if not relative:
                    _extern.remove_preset(preset)

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
@click.argument("topics", nargs=-1, required=False)
@click.argument("complete", type=bool)
def tab(topics, complete):
    """Utility sub-command for tabcompletion

    This command is meant to be called by a tab completion
    function and is given a the currently entered topics,
    along with a boolean indicating whether or not the
    last entered argument is complete.

    """

    # Discard `be tab`
    topics = list(topics)[2:]

    # When given an incomplete argument,
    # the argument is *sometimes* returned twice (?)
    # .. note:: Seen in Git Bash on Windows
    # $ be in giant [TAB]
    # -> ['giant']
    # $ be in gi[TAB]
    # -> ['gi', 'gi']
    if len(topics) > 1 and topics[-1] == topics[-2]:
        topics.pop()

    # Suggest projects
    if len(topics) == 0:
        projects = lib.list_projects(root=_extern.cwd())
        sys.stdout.write(" ".join(projects))

    elif len(topics) == 1:
        project = topics[0]
        projects = lib.list_projects(root=_extern.cwd())

        # Complete project
        if not complete:
            projects = [i for i in projects if i.startswith(project)]
            sys.stdout.write(" ".join(projects))
        else:
            # Suggest items from inventory
            inventory = _extern.load_inventory(project)
            inventory = lib.list_inventory(inventory)
            items = [i for i, b in inventory]
            sys.stdout.write(" ".join(items))

    else:
        project, item = topics[:2]

        # Complete inventory item
        if len(topics) == 2 and not complete:
            inventory = _extern.load_inventory(project)
            inventory = lib.list_inventory(inventory)
            items = [i for i, b in inventory]
            items = [i for i in items if i.startswith(item)]
            sys.stdout.write(" ".join(items))

        # Suggest items from template
        else:
            try:
                be = _extern.load_be(project)
                templates = _extern.load_templates(project)
                inventory = _extern.load_inventory(project)

                item = topics[-1]
                items = lib.list_template(root=_extern.cwd(),
                                          topics=topics,
                                          templates=templates,
                                          inventory=inventory,
                                          be=be)
                if not complete:
                    items = lib.list_template(root=_extern.cwd(),
                                              topics=topics[:-1],
                                              templates=templates,
                                              inventory=inventory,
                                              be=be)
                    items = [i for i in items if i.startswith(item)]
                    sys.stdout.write(" ".join(items) + " ")
                else:
                    sys.stdout.write(" ".join(items) + " ")

            except IndexError:
                sys.exit(lib.NORMAL)


@main.command()
def activate():
    """Enter into an environment with support for tab-completion

    This command drops you into a subshell, similar to the one
    generated via `be in ...`, except no topic is present and
    instead it enables tab-completion for supported shells.

    See documentation for further information.
    https://github.com/mottosso/be/wiki/cli

    """

    parent = lib.parent()

    try:
        cmd = lib.cmd(parent)
    except SystemError as exc:
        lib.echo(exc)
        sys.exit(lib.PROGRAM_ERROR)

    # Store reference to calling shell
    context = lib.context(root=_extern.cwd())
    context["BE_SHELL"] = parent

    if lib.platform() == "unix":
        context["BE_TABCOMPLETION"] = os.path.join(
            os.path.dirname(__file__), "_autocomplete.sh").replace("\\", "/")

    context.pop("BE_ACTIVE", None)

    sys.exit(subprocess.call(cmd, env=context))


@main.command()
@click.argument("topics", nargs=-1, required=False)
def ls(topics):
    """List contents of current context

    \b
    Usage:
        $ be ls
        - spiderman
        - hulk
        $ be ls spiderman
        - peter
        - mjay
        $ be ls spiderman seq01
        - 1000
        - 2000
        - 2500

    Return codes:
        0 Normal
        2 When insufficient arguments are supplied,
            or a template is unsupported.

    """

    if self.isactive():
        lib.echo("ERROR: Exit current project first")
        sys.exit(lib.USER_ERROR)

    # List projects
    if len(topics) == 0:
        for project in lib.list_projects(root=_extern.cwd()):
            lib.echo("- %s (project)" % project)
        sys.exit(lib.NORMAL)

    # List inventory of project
    elif len(topics) == 1:
        inventory = _extern.load_inventory(topics[0])
        for item, binding in lib.list_inventory(inventory):
            lib.echo("- %s (%s)" % (item, binding))
        sys.exit(lib.NORMAL)

    # List specific portion of template
    else:
        try:
            project = topics[0]
            be = _extern.load_be(project)
            templates = _extern.load_templates(project)
            inventory = _extern.load_inventory(project)
            for item in lib.list_template(root=_extern.cwd(),
                                          topics=topics,
                                          templates=templates,
                                          inventory=inventory,
                                          be=be):
                lib.echo("- %s" % item)
        except IndexError as exc:
            lib.echo(exc)
            sys.exit(lib.USER_ERROR)

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
    $ be find ad
    https://github.com/mottosso/be-ad.git

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

    Environment is outputted in a YAML-friendly format

    \b
    Usage:
        $ be dump
        Prefixed:
        - BE_TOPICS=hulk bruce animation
        - ...

    """

    if not self.isactive():
        lib.echo("ERROR: Enter a project first")
        sys.exit(lib.USER_ERROR)

    # Print custom environment variables first
    custom = sorted(os.environ.get("BE_ENVIRONMENT", "").split())
    if custom:
        lib.echo("Custom:")
        for key in custom:
            lib.echo("- %s=%s" % (key, os.environ.get(key)))

    # Then print redirected variables
    project = os.environ["BE_PROJECT"]
    root = os.environ["BE_PROJECTSROOT"]
    be = _extern.load(project, "be", optional=True, root=root)
    redirect = be.get("redirect", {}).items()
    if redirect:
        lib.echo("\nRedirect:")
        for map_source, map_dest in sorted(redirect):
            lib.echo("- %s=%s" % (map_dest, os.environ.get(map_dest)))

    # And then everything else
    prefixed = dict((k, v) for k, v in os.environ.iteritems()
                    if k.startswith("BE_"))
    if prefixed:
        lib.echo("\nPrefixed:")
        for key in sorted(prefixed):
            if not key.startswith("BE_"):
                continue
            lib.echo("- %s=%s" % (key, os.environ.get(key)))

    sys.exit(lib.NORMAL)


@main.command(name="?")
def what():
    """Print current topics"""

    if not self.isactive():
        lib.echo("No topic")
        sys.exit(lib.USER_ERROR)

    lib.echo(os.environ.get("BE_TOPICS", "This is a bug"))


if __name__ == '__main__':
    main()
