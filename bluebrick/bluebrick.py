# Copyright 2019 Virantha N. Ekanayake  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""

Usage:
    bluebrick.py [options] PARAMFILE all
    bluebrick.py [options] PARAMFILE (%s)...
    bluebrick.py --conf=FILE
    bluebrick.py -h

Arguments:
    PARAMFILE   YAML file with inputs
    all         Run all steps in the flow (%s)
%s

Options:
    -h --help        show this message
    -v --verbose     show more information
    -d --debug       show even more information
    --rundir=PATH    set path for running simulations in [default: runs] 
    --conf=FILE      load options from file

"""

from docopt import docopt
import yaml
import sys, os, logging, shutil
from collections import OrderedDict
from schema import Schema, And, Optional, Or, Use, SchemaError



from version import __version__
from utils import ordered_load, merge_args



"""
   
.. automodule:: bluebrick
    :private-members:
"""

class BlueBrick:
    """
        The main clas.  Performs the following functions:

    """

    def __init__ (self):
        """ 
        """
        self.args = None
        self.flow = OrderedDict([ ('download', 'Download all transactions from accounts'),
                                  ('qif',      'Save downloaded transactions to qif'),
                                  ('ofx',      'Save downloaded transactions to ofx'),
                      ])




    def get_options(self, argv):
        """
            Parse the command-line options and set the following object properties:

            :param argv: usually just sys.argv[1:]
            :returns: Nothing

            :ivar debug: Enable logging debug statements
            :ivar verbose: Enable verbose logging
            :ivar config: Dict of the config file

        """
        padding = max([len(x) for x in self.flow.keys()]) # Find max length of flow step names for padding with white space
        docstring = __doc__ % ('|'.join(self.flow), 
                              ','.join(self.flow.keys()),
                              '\n'.join(['    '+k+' '*(padding+4-len(k))+v for k,v  in self.flow.items()]))
        args = docopt(docstring, version=__version__)

        # Load in default conf values from file if specified
        if args['--conf']:
            with open(args['--conf']) as f:
                conf_args = yaml.load(f)
        else:
            conf_args = {}
        args = merge_args(conf_args, args)

        schema = Schema({
            'PARAMFILE': Use(open, error='PARAMFILE should be readable'),
            object: object
            })
        try:
            args = schema.validate(args)
        except SchemaError as e:
            exit(e)

        if args['all'] == 0:
            for f in list(self.flow):
                if args[f] == 0: del self.flow[f]
            logging.info("Doing flow steps: %s" % (','.join(self.flow.keys())))

        self.parameters = ordered_load(args['PARAMFILE'])
        self.run_dir = args['--rundir']

        if args['--debug']:
            logging.basicConfig(level=logging.DEBUG, format='%(message)s')
        elif args['--verbose']:
            logging.basicConfig(level=logging.INFO, format='%(message)s')   

        self.args = args # Just save this for posterity



    def go(self, argv):
        """ 
            The main entry point into BlueBrick

            #. Do something
            #. Do something else
        """
        # Read the command line options
        self.get_options(argv)


def main():
    script = BlueBrick()
    script.go(sys.argv[1:])

if __name__ == '__main__':
    main()


