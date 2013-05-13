#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from cloud_copasi.web_interface.models import CondorJob, Subtask
from cloud_copasi.web_interface.aws import task_tools

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
    
    def submit_subtask(self, index=0):
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
        subtask.index = subtask_count + 1
        subtask.type = type
        subtask.status = 'inactive'
        subtask.active = False
        subtask.save()
    
    def get_subtask(self, index):
        #Get a particular subtask by index
        subtasks = Subtask.objects.filter(task=self.task)
        
        return subtasks.get(index=index)
    
    def request_file_transfer(self, index):
        pass
    
    def notify_subtask(self, subtask, spec_files, other_files):
        #Notify the queue that we have a new subtask to run
        #spec files: list of the condor spec files
        #other files: list of any other s3 keys that need to be copied
        
        #Mark the subtask as ready to queue
        subtask.status = 'ready'
        subtask.save()
        
        #Notify the queue that we are submitting a new condor TASK
        task_tools.notify_new_condor_task(self.task, other_files, spec_files)
        
        subtask.status = 'submitted'
        subtask.active = True
        subtask.save()
        
        self.task.status='running'
        self.task.save()
        
    def notify_file_transfer(self, reason, file_list, zip, delete):
        """Notify the queue that we want the master to transfer files to s3
        """
        task_tools.notify_file_transfer(self.task, reason, file_list, zip, delete)
        self.task.status='transfer'
        self.task.save()