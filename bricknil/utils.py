import yaml
from collections import OrderedDict

def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    """ Helper function to allow yaml load routine to use an OrderedDict instead of regular dict.
        This helps keeps things sane when ordering the runs and printing out routines
    """
    class OrderedLoader(Loader):
        pass
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


def merge_args(conf_args, orig_args):
    """ Return new dict with args, and then conf_args merged in.
        Make sure that any keys in conf_args are also present in args
    """
    args = {}
    for k in conf_args.keys():
        if k not in orig_args:
            print("ERROR: Configuration file has unknown option %s" % k)
            sys.exit(-1)

    args.update(orig_args)
    args.update(conf_args)
    return args
