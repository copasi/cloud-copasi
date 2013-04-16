#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from cloud_copasi.web_interface.task_plugins.base import BaseTask
from cloud_copasi.web_interface.models import Task, CondorJob
from cloud_copasi.web_interface.models import Subtask
from django.forms import Form
from cloud_copasi.copasi.model import CopasiModel
from cloud_copasi.web_interface.aws import task_tools
import os

internal_type = ('sensitivity_optimization', 'Sensitivity optimization')

class TaskForm(Form):
    #Any extra fields for the task submission form
    pass

class TaskPlugin(BaseTask):
    
    subtasks = 2

    def validate(self):
        #TODO:Abstract this to a new COPASI class in this plugin package
        copasi_model = CopasiModel(self.task.original_model)
        isvalid = copasi_model.is_valid('SO')
        if isvalid != True:
            raise Exception(isvalid)

    def initialize_subtasks(self):
        #Create new subtask objects, and save them
        
        #Create the main subtask
        self.create_new_subtask('main')
        #And a subtask to process any results
        self.create_new_subtask('process')
        
    def process_subtask(self, index):
        """Prepare the indexed subtask"""
        
        if index == 0:
            self.process_first_subtask()
        else:
            raise Exception('No subtasks remaining')
        
    def process_first_subtask(self):
        #Get the first subtask
        subtask = self.get_subtask(0)
        
        #Construct the model files for this task
        copasi_model = CopasiModel(self.task.original_model)
        
        model_path, model_filename = os.path.split(self.task.original_model)
        
        #If no load balancing step required:
        model_files = copasi_model.prepare_so_task()
        condor_job_info_list = copasi_model.prepare_so_condor_jobs()
        
        spec_files = []
        other_files = []
        
        for condor_job_info in condor_job_info_list:
            condor_job = CondorJob()
            condor_job.subtask = subtask
            
            condor_job.spec_file = condor_job_info['spec_file']
            spec_files.append(condor_job_info['spec_file'])
            
            condor_job.std_output_file = condor_job_info['std_output_file']
            condor_job.std_error_file  = condor_job_info['std_error_file']
            condor_job.log_file = condor_job_info['log_file']
            condor_job.job_output = condor_job_info['job_output']
            
            condor_job.copasi_file = condor_job_info['copasi_file']
            other_files.append(condor_job_info['copasi_file'])
            
            condor_job.queue_status='C' # Not copied

            condor_job.save()
        
        #Add the original model filename to the list of files to transfer    
        other_files.append(model_filename)
        
        file_list = spec_files + other_files
        #Copy the necessary files over to S3
        task_tools.store_to_outgoing_bucket(self.task, model_path, file_list, delete=True)
        
        
        
        #Mark the subtask as ready to queue
        subtask.status = 'ready'
        subtask.save()
        
        #Notify the queue that we are submitting a new condor TASK
        task_tools.notify_new_condor_task(self.task, other_files, spec_files)
        
        subtask.status = 'queued'
        subtask.save()
        
        self.task.status='R'
        self.task.save()