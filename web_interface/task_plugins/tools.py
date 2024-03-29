#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

import os, glob, sys, importlib
from web_interface.task_plugins import plugins as task_plugins
import logging

log = logging.getLogger(__name__)

#Get a list of the subpackages in the module path
#Must contain plugin.py
def get_subpackages(path):
    directory =path[0]
    def is_plugin_package(d):
        d = os.path.join(directory, d)
        return os.path.isdir(d) and glob.glob(os.path.join(d, '__init__.py*')) and glob.glob(os.path.join(d, 'plugin.py*'))

    return filter(is_plugin_package, os.listdir(directory))

#Go through the list of packages and get the task_type tuple
def get_task_types(subpackages=None):
    if not subpackages:
        log.debug('get_task_types() in tools.py -------|')
        log.debug(task_plugins.__path__)
        subpackages = get_subpackages(task_plugins.__path__)

    output = []
    for package in subpackages:
        a=task_plugins
        module = importlib.import_module(task_plugins.__name__ + '.' + package + '.plugin')
        task_type = module.internal_type
        output.append(task_type)

    return output

def get_task_display_name(name):
    types = get_task_types()
    for internal_name, display_name in types:
        if internal_name == name:
            return display_name
    return 'Unknown'
#task_types = get_task_types(subpackages)
def get_task_class(task_type):
    module = importlib.import_module(task_plugins.__name__ + '.' + task_type + '.plugin')
    plugin = getattr(module, 'TaskPlugin')

    return plugin

def get_form_class(task_type):
    """Return the task form from str task_type"""
    module = importlib.import_module(task_plugins.__name__ + '.' + task_type + '.plugin')

    plugin = getattr(module, 'TaskForm')
    return plugin
