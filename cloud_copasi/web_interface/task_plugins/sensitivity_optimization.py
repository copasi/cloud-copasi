#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from cloud_copasi.web_interface.task_plugins.base import BaseTask
from web_interface.models import Task
from cloud_copasi.web_interface.models import Subtask

class SOTask(BaseTask):
    internal_name = ('SO', 'Sensitivity optimization')
    

    def prepare_next_subtask(self):
        
        #Get the subtasks associated with this task
        
        subtasks = Subtask.objects.filter(task=self.task)
        
        #Do we have any subtasks already running?
        
    