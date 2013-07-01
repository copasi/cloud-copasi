#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

import os, glob, sys, importlib
from cloud_copasi.web_interface import task_plugins
#Get a list of the subpackages in the module path
#Must contain plugin.py
def get_subpackages(path):
    directory =path[0]
    def is_plugin_package(d):
        d = os.path.join(directory, d)
        return os.path.isdir(d) and glob.glob(os.path.join(d, '__init__.py*')) and glob.glob(os.path.join(d, 'plugin.py*'))

    return filter(is_plugin_package, os.listdir(directory))

#Go through the list of packages and get the task_type tuple
def get_task_types(subpackages):
    output = []
    for package in subpackages:
        module = importlib.import_module(__package__ + '.' + package + '.plugin')
        task_type = module.internal_type
        output.append(task_type)
    return output

subpackages = get_subpackages(task_plugins.__path__)

task_types = get_task_types(subpackages)
