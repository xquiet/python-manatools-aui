#!/usr/bin/env python3
from setuptools import setup
from setuptools.command.develop import develop
from distutils.cmd import Command
import urllib.request
import io
import os

# load version variables from manatools/version.py
_version_file = os.path.join(os.path.dirname(__file__), "manatools", "version.py")
with io.open(_version_file, "r", encoding="utf-8") as vf:
    exec(vf.read())

# Read long description if README.md exists
_long_description = ""
_readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(_readme_path):
    with io.open(_readme_path, "r", encoding="utf-8") as rf:
        _long_description = rf.read()

# ---------------------------------------------------------------------------
# Bootstrap vendor assets
# ---------------------------------------------------------------------------

_BOOTSTRAP_VERSION = "5.3.3"
_BOOTSTRAP_BASE = f"https://cdn.jsdelivr.net/npm/bootstrap@{_BOOTSTRAP_VERSION}/dist"
_VENDOR_DIR = os.path.join(
    os.path.dirname(__file__),
    "manatools", "aui", "backends", "web", "static", "vendor", "bootstrap",
)
_BOOTSTRAP_ASSETS = {
    "bootstrap.min.css":        f"{_BOOTSTRAP_BASE}/css/bootstrap.min.css",
    "bootstrap.bundle.min.js":  f"{_BOOTSTRAP_BASE}/js/bootstrap.bundle.min.js",
}


class BootstrapAssetsCommand(Command):
    """Download Bootstrap vendor assets into the web backend static directory.

    Usage:
        python setup.py bootstrap_assets
    """
    description = "download Bootstrap vendor assets (CSS + JS) for the web backend"
    user_options = []

    def initialize_options(self): pass
    def finalize_options(self): pass

    def run(self):
        os.makedirs(_VENDOR_DIR, exist_ok=True)
        for filename, url in _BOOTSTRAP_ASSETS.items():
            dest = os.path.join(_VENDOR_DIR, filename)
            if os.path.exists(dest):
                print(f"  already present, skipping: {filename}")
                continue
            print(f"  downloading {filename} ...", end=" ", flush=True)
            try:
                urllib.request.urlretrieve(url, dest)
                print("ok")
            except Exception as exc:
                print(f"FAILED ({exc})")
                raise SystemExit(1) from exc
        print(f"Bootstrap {_BOOTSTRAP_VERSION} assets ready in {_VENDOR_DIR}")


class DevelopWithAssets(develop):
    """Extend 'develop' so that 'pip install -e .' also fetches the assets."""
    def run(self):
        self.run_command("bootstrap_assets")
        super().run()


# ---------------------------------------------------------------------------

setup(
    name=__project_name__,
    version=__project_version__,
    author='Angelo Naselli, Matteo Pasotti',
    author_email='anaselli@linux.it, xquiet@coriolite.com',
    packages=[
        'manatools',
        'manatools.aui',
        'manatools.aui.backends',
        'manatools.aui.backends.qt',
        'manatools.aui.backends.gtk',
        'manatools.aui.backends.curses',
        'manatools.aui.backends.web',
        'manatools.ui',
    ],
    package_data={
        'manatools.aui.backends.web': [
            'templates/*.html',
            'static/css/*.css',
            'static/js/*.js',
            'static/vendor/bootstrap/*.css',
            'static/vendor/bootstrap/*.js',
        ],
    },
    include_package_data=True,
    license='LGPLv2+',
    description='Python ManaTools framework.',
    long_description=_long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "dbus-python",
        "python-gettext",
        "PyYAML",
    ],
    cmdclass={
        'bootstrap_assets': BootstrapAssetsCommand,
        'develop':          DevelopWithAssets,
    },
)