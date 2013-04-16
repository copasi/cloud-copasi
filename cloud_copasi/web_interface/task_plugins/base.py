#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from cloud_copasi.web_interface.models import CondorJob, Subtask

#===============================================================================
# Base task plugin structure
#===============================================================================



class BaseTask:
    
    internal_name = ('base', 'Base task')
    
    #The number of subtasks this task is split into
    subtasks=0
    
    def __init__(self, task):
        self.task = task
    
    def validate(self):
        return True
    
    def prepare_subtask(self, index=0):
        """Prepare a particular subtask to run
        """
        
        #Ensure the correct files are on the system
        return []
    
    def initialize_subtasks(self):
        pass
    
    def create_new_subtask(self, type):
        #Get a count of the number of existing subtasks
        subtask_count = len(Subtask.objects.filter(task=self.task))
        
        subtask =  Subtask()
        subtask.task = self.task
        subtask.index = subtask_count
        subtask.type = type
        subtask.status = 'new'
        subtask.save()
    
    def get_subtask(self, index):
        #Get a particular subtask by index
        subtasks = Subtask.objects.filter(task=self.task)
        
        return subtasks.get(index=index)