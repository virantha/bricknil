from invoke import task
from bluebrick.version import __version__

@task
def pypi(c):
    c.run('python setup.py bdist_wheel')
    c.run(f'python -m twine upload dist/bluebrick-{__version__}-py3-none-any.whl')

@task
def docs(c):
    githubpages = "/Users/virantha/dev/githubdocs/bluebrick"
    with c.cd(githubpages):
        c.run('git checkout gh-pages')
        c.run('git pull origin gh-pages')
    #c.run("head CHANGES.rst > CHANGES_RECENT.rst")
    #c.run("tail -n 1 CHANGES.rst >> CHANGES_RECENT.rst")
    with c.cd("docs"):
        print("Running sphinx in docs/ and building to ~/dev/githubpages/bluebrick")
        c.run("make clean")
        c.run('rm -rf _auto_summary')
        c.run("make html")
        #c.run("cp -R ../test/htmlcov %s/html/testing" % githubpages)
    with c.cd(githubpages):
        #c.run("mv html/* .")
        c.run("git add .")
        c.run('git commit -am "doc update"')
        c.run('git push origin gh-pages')
