import os
import sys
from nose.tools import *
from be.vendor.click.testing import CliRunner

import be.cli
import be._extern

self = sys.modules[__name__]
self.test_templates = {
    "asset": "{cwd}/{project}/assets/{item}/{type}",
    "shot": "{cwd}/{project}/shots/{item}/{type}"
}
self.test_inventory = {
    "asset": ["peter", "maryjane"],
    "shot": [1000, 2000]
}


def setup():
    os.environ["BE_TESTING"] = "1"


def teardown():
    os.environ.pop("BE_TESTING")


def clean_setup():
    self.cwd = os.getcwd()
    self._dt = be._extern.default_templates
    self._di = be._extern.defaults_inventory

    be._extern.default_templates = self.test_templates
    be._extern.defaults_inventory = self.test_inventory


def clean_teardown():
    be._extern.default_templates = self._dt
    be._extern.defaults_inventory = self._di
    os.chdir(self.cwd)


def invoke(runner, args):
    return runner.invoke(be.cli.main, args)


def test_new():
    """$be new"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = invoke(runner, ["new", "spiderman"])
        assert_true("created" in result.output.split("\n")[0])


@with_setup(clean_setup, clean_teardown)
def test_in():
    """$be in"""

    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = os.getcwd().replace("\\", "/")
        invoke(runner, ["new", "spiderman"])
        invoke(runner, ["in", "spiderman/peter/model", "-y"])
        new_cwd = self.test_templates["asset"].format(
            cwd=cwd,
            project="spiderman",
            item="peter",
            type="model").replace("\\", "/")
        assert_equals(os.getcwd().replace("\\", "/"), new_cwd)
