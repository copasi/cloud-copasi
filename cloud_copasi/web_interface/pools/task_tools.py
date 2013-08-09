#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from boto import s3, sqs
import json, os, sys
from cloud_copasi.web_interface.aws import s3_tools
from cloud_copasi.web_interface.models import Task, CondorJob, Subtask
from boto.s3.key import Key
from cloud_copasi.web_interface.aws import aws_tools
from boto.sqs.message import Message
from cloud_copasi.web_interface.task_plugins import tools
import logging
from cloud_copasi.web_interface.pools import condor_tools

log = logging.getLogger(__name__)
#Note: 31/7/2013, rewritten to support only local task submission with Bosco


def update_tasks(user=None, task=None):
    """Examines the status of all CondorJob objects. If the status of upstream subtasks and tasks need changing, then this is done.
    If requested, can filter by a specific user or subtask
    """
    
    
    #Step 1: Get a list of running tasks
    log.debug('Checking running tasks')
    tasks = Task.objects.filter(status='running')
    if user:
        tasks = tasks.filter(condor_pool__user = user)
    if task:
        tasks = tasks.filter(id=task.id)
    
    for task in tasks:
        #Next, get the corresponding running subtasks
        subtasks = Subtask.objects.filter(task=task).filter(status='running')
        log.debug(subtasks)
        for subtask in subtasks:
            log.debug('Checking subtask status: %s'%subtask.status)
            jobs = CondorJob.objects.filter(subtask=subtask)
            
            
            #Does any of the jobs have an error status? Then mark the whole task as having failed
            errors = jobs.filter(status='E') | jobs.filter(status='H')
            if errors.count() > 0:
                for job in errors:
                    log.debug('Job %d.%d has status %s. Marking task as errored' % (job.subtask.cluster_id, job.process_id, job.status))
                subtask.status = 'error'
                subtask.task.status = 'error'
                subtask.save()
                task.save()
                break
                #TODO: Can we have a more graceful error handling procedure here?
                
            
            #Next, check to see if all the jobs have finished
            finished = jobs.filter(status='F')
            if finished.count() == jobs.count():
                log.debug('Task %s, subtask %d: all jobs marked as finished. Checking logs' %(task.name, subtask.index))
                #The subtask has finished!
                if check_log(subtask):
                    log.debug('Task %s, subtask %d: successfully finished. Updating status' % (task.name, subtask.index))
                    subtask.status = 'finished'
                    subtask.save()
                    
                    #Is there another subtask to run?
                    task_class = tools.get_task_class(subtask.task.task_type)
                    if subtask.index < task_class.subtasks:
                        log.debug('Preparing new subtask %d' % (subtask.index + 1))
                        #Then we have another subtask to prepare and run! (wohoo!)
                        new_subtask = task_class.prepare_subtask(subtask.index + 1)
                        condor_tools.submit_task(new_subtask)
                    else:
                        #Otherwise the task must have finished. Excellent news.
                        log.debug('Task %s: all subtasks complete. Marking task as finished')
                        task.status='finished'
                        
            else:
                #Something not right. TODO: determine if bad exit status, files not transferred yet, etc., and respond appropriatley
                log.debug('message')
            
    

def check_log(subtask):
    """Checks the logs of each of the condor jobs to determine the status of the condor jobs.
    """
    
    #for job in subtask.condor_job__set
    #Step 1 - open the log for each subtask
    ##TODO:
    
    #Step 2 - check the exit status
    ##TODO:
    
    #Step 3 - Read the running time
    ##TODO:
    
    #Step 4 - Check the output file exists and has content
    ##TODO:
    
    #Step 5 - Save the changes
    #job.save()
    
    #Step 6 - If everything went ok here, then save the changes to the subtask and task()
    
    return True


def delete_task(task):
    pass
    #TODO: