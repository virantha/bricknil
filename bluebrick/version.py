import yaml, pkg_resources

resource_package = __name__
#resource_path = '/'.join(('bluebrick', 'version.yml'))
resource_path = 'config.yml'
config = pkg_resources.resource_stream(resource_package, resource_path)

d = yaml.load(config)
__version__ = d['version']
