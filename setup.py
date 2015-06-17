import os
import imp
from setuptools import setup, find_packages

version_file = os.path.abspath("be/version.py")
version_mod = imp.load_source("version", version_file)
version = version_mod.version


classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Utilities"
]

setup(
    name="be",
    version=version,
    description="Minimal asset management system",
    long_description="Visit https://github.com/mottosso/be",
    author="Abstract Factory",
    author_email="marcus@abstractfactory.com",
    url="https://github.com/mottosso/be",
    license="LGPLv2.1",
    packages=find_packages(),
    zip_safe=False,
    classifiers=classifiers,
    package_data={
        "be": ["*.sh", "*.bat"],
        "be.vendor.requests": ["cacert.pem"]
    },
    entry_points={
        "console_scripts": ["be = be.cli:main"]
    }
)

if os.name != "nt":
    import os
    if "BE_BITSET" not in os.environ:
        import subprocess
        shell = os.path.dirname(__file__)
        shell = os.path.join(shell, "be", "_shell.sh")
        print "Setting executable bit on %s" % shell
        if subprocess.call(["chmod", "+x", shell]) != 0:
            print "WARNING: Could not set executable bit on subshell"
        os.environ["BE_BITSET"] = "1"
