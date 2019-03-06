# Copyright 2019 Virantha N. Ekanayake 
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Super-class of all the Tasks in the event-loop
"""
from enum import Enum
import logging


class Process:
    """Subclass this for anything going into the Async Event Loop
        
       This class keeps track of a unique numeric ID for each process, and its name.
       It also provides some utilty functions to log messages at various levels.

       Attributes:
          id (int) : Process ID (unique)
          name (str):  Human readable name for process (does not need to be unique)

    """

    _next_id = 0  

    def __init__(self, name):
        self.name = name

        # Assign ID
        self.id = Process._next_id
        Process._next_id += 1

        self.logger = logging.getLogger(str(self))

    def __str__(self):
        return f'{self.name}.{self.id}'

    def __repr__(self):
        return f'{type(self).__name__}("{self.name}")'

    def message(self, m : str , level = logging.INFO):
        """Print message *m* if its level is lower than the instance level"""

        if level == logging.DEBUG:
            self.logger.debug(m)
        elif level == logging.INFO:
            self.logger.info(m)
        elif level == logging.ERROR:
            self.logger.error(m)

    def message_info(self, m):
        """Helper function for logging messages at INFO level"""
        self.message(m, logging.INFO)

    def message_debug(self, m):
        """Helper function for logging messages at DEBUG level"""
        self.message(m, logging.DEBUG)

    def message_error(self, m):
        """Helper function for logging messages at ERROR level"""
        self.message(m, logging.ERROR)
