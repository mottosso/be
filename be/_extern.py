"""External access module

Attributes:
    self.cache: Store configuration files after having been loaded
    self.headers: Optional GitHub authentication headers
    self.files: Files supported in remote presets
    self.verbose: Whether or not to output debugging messages
"""

import os
import re
import sys
import stat
import json
import shutil
import tarfile
import tempfile

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
self.cache = dict()
self.suffix = ".bat" if os.name == "nt" else ".sh"
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


def parse_environment(environment, existing):
    environment = _join_environment(environment)
    environment = _resolve_environment(environment, existing)
    return environment


def load_settings(project):
    return load(project, "be", optional=True)


def load_templates(project):
    """Return templates given name of project

    Arguments:
        project (str): Name of project

    """

    return _resolve_references(load(project, "templates"))


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
                    "ERROR: %s.yaml not defined "
                    "for project \"%s\"" % (fname, project))
                sys.exit(lib.USER_ERROR)

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
    """requests.get wrapper"""
    token = os.environ.get(BE_GITHUB_API_TOKEN)
    if token is not None:
        kwargs["headers"] = {
            "Authorization": "token %s" % token
        }

    try:
        response = requests.get(path, verify=False, **kwargs)
        if response.status_code == 403:
            lib.echo("Patience: You can't pull more than 60 "
                     "presets per hour without an API token.\n"
                     "See https://github.com/mottosso/be/wiki/advanced#extended-preset-access")
            sys.exit(lib.USER_ERROR)
        return response
    except Exception as e:
        if self.verbose:
            lib.echo("ERROR: %s" % e)
        else:
            lib.echo("ERROR: Something went wrong. "
                     "See --verbose for more information")


def repo_is_preset(repo):
    """Evaluate whether repo is a be package

    Arguments:
        repo (dict): GitHub response with contents of repo

    """

    package_template = "https://raw.githubusercontent.com/{repo}/master/package.json"
    package_path = package_template.format(repo=repo)

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


def fetch_release(repo):
    """Return latest release from `repo`

    Arguments:
        repo (str): username/repo combination

    """

    return repo


def download_file(url):
    local_filename = url.split('/')[-1]
    r = requests.get(url, stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): 
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
    return local_filename


def pull_preset(repo, preset_dir):
    repo, tag = repo.split(":", 1) + [None]

    if not repo.count("/") == 1 or len(repo.split("/")) != 2:
        raise ValueError("Repository syntax is: "
                         "username/repo (not %s)" % repo)

    if not repo_is_preset(repo):
        lib.echo("ERROR: %s does not appear to be a preset, "
                  "try --verbose for more information." % repo)
        sys.exit(lib.USER_ERROR)

    url = "https://api.github.com/repos/%s/tarball" % repo
    r = get(url, stream=True)

    tempdir = tempfile.mkdtemp()
    temppath = "/".join([tempdir, repo.rsplit("/", 1)[-1] + ".tar.gz"])
    with open(temppath, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            if not chunk:
                continue
            f.write(chunk)
            f.flush()

    try:
        return unzip_preset(temppath, preset_dir)
    finally:
        shutil.rmtree(tempdir)


def unzip_preset(src, dest):
    tempdir = os.path.dirname(src)
    
    if self.verbose:
        lib.echo("Unpacking %s -> %s" % (src, tempdir))
    
    try:
        tar = tarfile.open(src)
        tar.extractall(tempdir)
    finally:
        tar.close()

    # GitHub tars always come with a single directory
    try:
        repo = [os.path.join(tempdir, d) for d in os.listdir(tempdir)
                if os.path.isdir(os.path.join(tempdir, d))][0]
    except:
        raise ValueError("%s is not a preset (this is a bug)" % src)

    if self.verbose:
        lib.echo("Moving %s -> %s" % (repo, dest))
    
    presets_dir()  # Create if it doesn't exist

    shutil.move(repo, dest)

    return dest


def local_presets():
    """Return local presets"""
    return os.listdir(presets_dir())


def github_presets():
    """Return remote presets hosted on GitHub"""
    addr = ("https://raw.githubusercontent.com"
            "/mottosso/be-presets/master/presets.json")
    return dict((package["name"], package["repository"])
                for package in get(addr).json().get("presets"))


def copy_preset(preset_dir, project_dir):
    """Copy contents of preset into new project

    If package.json contains the key "contents", limit
    the files copied to those present in this list.

    Arguments:
        preset_dir (str): Absolute path to preset
        project_dir (str): Absolute path to new project

    """

    os.makedirs(project_dir)

    package_file = os.path.join(preset_dir, "package.json")
    with open(package_file) as f:
        package = json.load(f)

    for fname in os.listdir(preset_dir):
        src = os.path.join(preset_dir, fname)

        contents = package.get("contents") or []

        if fname not in self.files + contents:
            continue

        if os.path.isfile(src):
            shutil.copy2(src, project_dir)
        else:
            dest = os.path.join(project_dir, fname)
            shutil.copytree(src, dest)


def _join_environment(environment):
    """Concatenate lists"""
    for key, value in environment.copy().iteritems():
        if isinstance(value, list):
            environment[key] = os.pathsep.join(value)
    return environment


def _parse_environment_pathsep(environment):
    """Replace Windows with Linux path-separators on Linux, and vice versa"""
    for key, value in environment.copy().iteritems():
        right, wrong = ";:" if os.name == "nt" else ":;"
        environment[key] = value.replace(wrong, right)
    return environment


def _resolve_environment(environment, existing):
    """Resolve $ occurences by expansion

    Given a dictionary {"PATH": "$PATH;somevalue"}
    Return {"PATH": "value_of_PATH;somevalue"}

    """

    def repl(match):
        key = pattern[match.start():match.end()].strip("$")
        if key not in existing:
            sys.stderr.write("ERROR: Unavailable environment variable: \"%s\"" % key)
            sys.exit(lib.USER_ERROR)
        return existing[key]

    pat = re.compile("\$\w+", re.IGNORECASE)
    for key, pattern in environment.copy().iteritems():
        environment[key] = pat.sub(repl, pattern)

    return environment


def _resolve_references(templates):
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
            sys.exit(lib.USER_ERROR)
        return templates[key]

    for key, pattern in templates.copy().iteritems():
        templates[key] = re.sub("{@\w+}", repl, pattern)

    return templates
