#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from cloud_copasi.web_interface.task_plugins.base import BaseTask, BaseTaskForm
from cloud_copasi.web_interface.models import Task, CondorJob, CondorPool
from cloud_copasi.web_interface.models import Subtask
from django.forms import Form
from django import forms
from cloud_copasi.copasi.model import CopasiModel
import os
import logging

log = logging.getLogger(__name__)

internal_type = ('sensitivity_optimization', 'Sensitivity optimization')

class TaskForm(BaseTaskForm):
    #Any extra fields for the task submission form
    pass


class TaskPlugin(BaseTask):
    
    subtasks = 2

    def __init__(self, *args, **kwargs):
        super(TaskPlugin, self).__init__(*args, **kwargs)
        self.copasi_model = CopasiModel(os.path.join(self.task.directory, self.task.original_model))
        

    def validate(self):
        #TODO:Abstract this to a new COPASI class in this plugin package
        return self.copasi_model.is_valid('SO')

    def initialize_subtasks(self):
        #Create new subtask objects, and save them
        
        #Create the main subtask
        self.create_new_subtask('main')
        #And a subtask to process any results
        self.create_new_subtask('process')
        
    def prepare_subtask(self, index):
        """Prepare the indexed subtask"""
        
        if index == 1:
            return self.process_first_subtask()
        elif index == 2:
            return self.process_second_subtask()
        else:
            raise Exception('No subtasks remaining')
        
#     def request_file_transfer(self, index, reason):
#         """Request the transfer of files to be transfered from the master back to s3 for a particular subtask
#         """
#         if index == 2:
#             self.request_all_files(reason)
        
    def process_first_subtask(self):
        #Get the first subtask
        subtask = self.get_subtask(1)
        
        #Construct the model files for this task
        
        
        model_path, model_filename = os.path.split(self.task.original_model)
        
        #If no load balancing step required:
        model_files = self.copasi_model.prepare_so_task()
        
        condor_pool = self.task.condor_pool
        
        condor_job_file = self.copasi_model.prepare_so_condor_job(condor_pool.pool_type, condor_pool.address, subtask_index=1, rank='')
        
        log.debug('Prepared copasi files %s'%model_files)
        log.debug('Prepared condor job %s' %condor_job_file)
        
        subtask.spec_file = condor_job_file
        subtask.status = 'ready'
        subtask.save()
        
        return subtask
        
        
    def process_second_subtask(self):
        print "nothing to see here!"
        subtask=self.get_subtask(2)
        #self.notify_subtask(subtask, [], [])
        
    def request_all_files(self, reason):
        #Get a list of all the files we would like to transfer back
        
        #Get the number of condor jobs in the first subtask
        subtask_1 = self.get_subtask(1)
        job_count = subtask_1.condorjob_set.all().count()
        parameter_count = job_count/2
        
        file_list=[]
        
        for i in range(parameter_count):
            for min in [1, 0]:
                file_list.append('auto_condor_%d.job' % (2*i + min))
                file_list.append('auto_copasi_%d.cps' % (2*i + min))
                file_list.append('auto_copasi_%d.cps.log' % (2*i + min))
                file_list.append('auto_copasi_%d.cps.out' % (2*i + min))
                file_list.append('auto_copasi_%d.cps.err' % (2*i + min))
        
        #self.notify_file_transfer(reason, file_list, zip=False, delete=False)