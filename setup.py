from __future__ import print_function
from setuptools import setup, find_packages

import io
import os
from setuptools import Command
import yaml, pkg_resources

with open('bluebrick/config.yml') as f:
    d = yaml.load(f)
    __version__ = d['version']

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
            buf.append(f.read())
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

print(required)
print(dependency_links)

setup (
    name = "bluebrick",
    version = __version__,
    #version = "0.5",
    description="Control LEGO(tm) BluetoothLE Hubs, Motors, and Sensors using Async Python",
    license = "ASL 2.0",
    long_description = long_description,
    author="Virantha N. Ekanayake",
    author_email="virantha@gmail.com", # Removed.
    package_data = {'': ['*.xml']},
    zip_safe = True,
    include_package_data = True,
    packages = packages,
    install_requires = required + ['pyobjc ; sys.platform == "darwin"'],
    dependency_links = dependency_links,
    entry_points = {
            'console_scripts': [
                    'bluebrick = bluebrick.bluebrick:main'
                ],
        },
    options = {
	    "pyinstaller": {"packages": packages}
	    },
    cmdclass = {'test':PyTest}

)
