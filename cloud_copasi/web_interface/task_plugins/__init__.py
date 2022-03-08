# #-------------------------------------------------------------------------------
# # Cloud-COPASI
# # Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
# # All rights reserved. This program and the accompanying materials
# # are made available under the terms of the GNU Public License v3.0
# # which accompanies this distribution, and is available at
# # http://www.gnu.org/licenses/gpl.html
# #-------------------------------------------------------------------------------
# 
# import os, glob, sys, importlib
# 
# #Get a list of the subpackages in the module path
# #Must contain plugin.py
# def get_subpackages(path):
#     directory =path[0]
#     def is_plugin_package(d):
#         d = os.path.join(directory, d)
#         return os.path.isdir(d) and glob.glob(os.path.join(d, '__init__.py*')) and glob.glob(os.path.join(d, 'plugin.py*'))
# 
#     return filter(is_plugin_package, os.listdir(directory))
# 
# 
# #Go through the list of packages and get the task_type tuple
# def get_task_types(subpackages):
#     output = []
#     for package in subpackages:
#         module = importlib.import_module(__package__ + '.' + package + '.plugin')
#         task_type = module.internal_type
#         output.append(task_type)
#     return output
# subpackages = get_subpackages(__path__)
# 
# task_types = get_task_types(subpackages)
# 
# #Method for loading a plugin and returning the TaskPlugin class (not instance)
# def get_class(name):
#     module = importlib.import_module(__package__ + '.' + name + '.plugin')
#     plugin = getattr(module, 'TaskPlugin')
#     return plugin