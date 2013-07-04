#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from cloud_copasi.web_interface.task_plugins.base import BaseTask, BaseTaskForm
from cloud_copasi.web_interface.models import Task, CondorJob
from cloud_copasi.web_interface.models import Subtask
from django.forms import Form
from django import forms
import os

internal_type = ('test_plugin', 'Test plugin')

class TaskForm(BaseTaskForm):
    #Any extra fields for the task submission form
    test_field_1 = forms.CharField(max_length=20, required=True)
    test_field_2 = forms.IntegerField()
    test_field_3 = forms.ChoiceField(choices=(('1', '111'),))

class TaskPlugin(BaseTask):
    
    subtasks = 2

    def validate(self):
        return 'invalid model'
    
    def initialize_subtasks(self):
        #Create new subtask objects, and save them
        
        #Create the main subtask
        pass
        
                
    def submit_subtask(self, index):
        """Prepare the indexed subtask"""
        
        pass
        
    def request_file_transfer(self, index, reason):
        """Request the transfer of files to be transfered from the master back to s3 for a particular subtask
        """
        pass
        
    