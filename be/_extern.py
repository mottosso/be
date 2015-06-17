"""External access module

Attributes:
    self.cache: Store configuration files after having been loaded
    self.home: Absolute path to the `be` Python package directory
    self.headers: Optional GitHub authentication headers
    self.files: Files supported in remote presets

"""

import os
import re
import sys
import stat
import shutil

from vendor import yaml
from vendor import requests

import lib

# Environment variables
BE_PRESETSDIR = "BE_PRESETSDIR"
BE_GITHUB_USERNAME = "BE_GITHUB_USERNAME"
BE_GITHUB_API_TOKEN = "BE_GITHUB_API_TOKEN"

# Temporarily disable warning about SSL on Python < 2.7.9
requests.packages.urllib3.disable_warnings()

self = sys.modules.get(__name__)
self.home = os.path.dirname(__file__)
self.cache = dict()
self.suffix = ".bat" if os.name == "nt" else ".sh"
self.headers = {
  "X-Github-Username": os.environ.get(BE_GITHUB_USERNAME),
  "X-Github-API-Token": os.environ.get(BE_GITHUB_API_TOKEN)
}
self.files = [
    "be.yaml",
    "inventory.yaml",
    "templates.yaml",
    "environment.yaml",
    "tasks.yaml",
    "users.yaml",
]
self.verbose = False


def home():
    """Return be Python package directory"""
    return os.path.dirname(__file__)


def cwd():
    """Return the be current working directory"""
    return os.getcwd().replace("\\", "/")


def load_settings(project):
    return load(project, "be", optional=True)


def load_environment(project):
    return load(project, "environment", optional=True)


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


def load(project, fname, optional=False, root=None):
    if fname not in self.cache:
        path = os.path.join(root or cwd(), project, "%s.yaml" % fname)
        try:
            with open(path) as f:
                self.cache[fname] = yaml.load(f) or dict()
        except IOError:
            if optional:
                self.cache[fname] = {}
            else:
                sys.stderr.write(
                    "PROJECT ERROR: %s.yaml not defined "
                    "for project \"%s\"" % (fname, project))
                sys.exit(1)

    return self.cache[fname]


def write_script(script, tempdir):
    """Write script to a temporary directory

    Arguments:
        script (list): Commands which to put into a file

    Returns:
        Absolute path to script

    """

    name = "script" + self.suffix
    path = os.path.join(tempdir, name)

    with open(path, "w") as f:
        f.write("\n".join(script))

    return path


def write_aliases(aliases, tempdir):
    """Write aliases to temporary directory

    Arguments:
        alias (dict): {name: value} dict of aliases

    """

    tempdir = os.path.join(tempdir, "aliases")
    os.makedirs(tempdir)

    for alias, cmd in aliases.iteritems():
        path = os.path.join(tempdir, alias)

        if os.name == "nt":
            path += ".bat"

        with open(path, "w") as f:
            f.write(cmd)

        if os.name != "nt":
            # Make executable on unix systems
            st = os.stat(path)
            os.chmod(path, st.st_mode | stat.S_IXUSR
                     | stat.S_IXGRP | stat.S_IXOTH)

    return tempdir


def projects():
    """Return list of available projects"""
    return os.listdir(cwd())


def presets_dir():
    """Return presets directory"""
    default_presets_dir = os.path.join(
        os.path.expanduser("~"), ".be", "presets")
    presets_dir = os.environ.get(BE_PRESETSDIR, default_presets_dir)
    if not os.path.exists(presets_dir):
        os.makedirs(presets_dir)
    return presets_dir


def remove_preset(preset):
    """Physically delete local preset

    Arguments:
        preset (str): Name of preset

    """

    preset_dir = os.path.join(presets_dir(), preset)

    try:
        shutil.rmtree(preset_dir)
    except IOError:
        lib.echo("\"%s\" did not exist" % preset)


def get(path, **kwargs):
    try:
        response = requests.get(path, verify=False, **kwargs)
        if response.status_code == 403:
            raise IOError("Patience: You can't pull more than 40 "
                          "presets per hour without an API token.")
        return response
    except Exception as e:
        if self.verbose:
            lib.echo(e)
        raise e


def repo_is_preset(repository):
    """Evaluate whether repository is a be package

    Arguments:
        response (dict): GitHub response with contents of repository

    """

    package_template = "https://raw.githubusercontent.com/{repository}/master/package.json"
    package_path = package_template.format(repository=repository)

    response = get(package_path)
    if response.status_code == 404:
        return False

    try:
        data = response.json()
    except:
        return False

    if not data.get("type") == "bepreset":
        return False

    return True


def fetch_release(repository):
    """Return latest release from `repository`

    Arguments:
        repository (str): username/repo combination

    """

    return repository


def pull_preset(repository, preset_dir):
    """Pull remote repository into `presets_dir`

    Arguments:
        repository (str): username/repo combination,
            e.g. mottosso/be-ad
        preset_dir (str): Absolute path in which to store preset

    """

    repository, tag = repository.split(":", 1) + [None]
    api_endpoint = "https://api.github.com/repos/" + repository

    kwargs = {}
    if self.headers["X-Github-Username"] is not None:
        kwargs["headers"] = self.headers

    response = get(api_endpoint + "/contents", **kwargs)

    if not repo_is_preset(repository):
        lib.echo("Error: %s does not appear to be a preset, "
                  "try --verbose for more information." % repository)
        sys.exit(1)

    if not os.path.exists(preset_dir):
        os.makedirs(preset_dir)

    for f in response.json():
        fname, download_url = f["name"], f["download_url"]
        if fname not in self.files:
            continue

        response = get(download_url)
        fpath = os.path.join(preset_dir, fname)
        with open(fpath, "w") as f:
            f.write(response.text)


def local_presets():
    """Return local presets"""
    return os.listdir(presets_dir())


def github_presets():
    """Return remote presets hosted on GitHub"""
    addr = ("https://raw.githubusercontent.com"
            "/mottosso/be-presets/master/presets.json")
    return dict((package["name"], package["repository"])
                for package in get(addr).json().get("presets"))


def copy_preset(preset_dir, dest):
    os.makedirs(dest)

    for fname in os.listdir(preset_dir):
        src = os.path.join(preset_dir, fname)
        shutil.copy2(src, dest)


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
