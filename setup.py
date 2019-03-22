from __future__ import print_function
from setuptools import setup, find_packages

import io
import os
from setuptools import Command
#from bricknil.version import __version__


# Load the package's __version__.py module as a dictionary.
here = os.path.abspath(os.path.dirname(__file__))
about = {}
with open(os.path.join(here, 'bricknil', 'version.py')) as f:
    exec(f.read(), about)

class PyTest(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        import sys,subprocess
        cwd = os.getcwd()
        os.chdir('test')
        errno = subprocess.call([sys.executable, 'runtests.py'])
        os.chdir(cwd)
        raise SystemExit(errno)

def read(*filenames, **kwargs):
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n')
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            headline_count = 0
            found_features = False
            for line in f.readlines():
                # Keep reading until we find the first headline
                # after Features
                if line.startswith('Features'):
                    found_features = True
                if line.startswith('####'):
                    headline_count += 1
                if found_features and headline_count == 2:
                    buf = buf[:-1]
                    break
                else:
                    buf.append(line.rstrip())
    return sep.join(buf)

packages = find_packages(exclude="tests")

long_description = read('README.rst')

required = []
dependency_links = []
with open("requirements.txt") as f:
    for line in f.read().splitlines():
        if line.startswith('git'):
            _, url = line.split('+')
            pkg_name = url[url.index('=')+1:]
            dependency_links.append(url)
            required.append(pkg_name)
        else:
            required.append(line)


setup (
    name = "bricknil",
    version = about['__version__'],
    description="Control LEGO(tm) BluetoothLE Hubs, Motors, and Sensors using Async Python",
    license = "ASL 2.0",
    long_description = long_description,
    author="Virantha N. Ekanayake",
    author_email="virantha@gmail.com", # Removed.
    url='https://virantha.github.io/bricknil',
    package_data = {'': ['*.xml']},
    zip_safe = True,
    include_package_data = True,
    packages = packages,
    install_requires = required + ['pyobjc ; sys.platform == "darwin"',
                                   'bricknil-bleak ; sys.platform != "darwin"'],
    dependency_links = dependency_links,
    entry_points = {
            'console_scripts': [
                    'bricknil = bricknil.bricknil:main'
                ],
        },
    options = {
	    "pyinstaller": {"packages": packages}
	    },
    cmdclass = {'test':PyTest}

)
