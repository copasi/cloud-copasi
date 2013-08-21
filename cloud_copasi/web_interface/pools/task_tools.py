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
import tarfile
import datetime
from django.utils.timezone import now

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
                subtask.finish_time = now()
                subtask.save()
                task.save()
                break
                #TODO: Can we have a more graceful error handling procedure here?
                
            
            #Next, check to see if all the jobs have finished
            finished = jobs.filter(status='F')
            if finished.count() == jobs.count():
                #The subtask has finished!
                log.debug('Task %s, subtask %d: successfully finished. Updating status' % (task.name, subtask.index))
                subtask.status = 'finished'
                subtask.set_run_time() #Set the run time as the sum from the associated jobs
                subtask.set_job_count() #And the number of condor jobs
                subtask.finish_time = now()
                subtask.save()
                    
            else:
                #Something not right. TODO: determine if bad exit status, files not transferred yet, etc., and respond appropriatley
                log.debug('%d jobs still in queue.' % (jobs.count() - finished.count()))
            
    
        #Now go through the subtasks and submit any that are waiting, provided that their preceding one has finished
        
        subtasks = Subtask.objects.filter(task=task).filter(status='waiting').order_by('index')
        for subtask in subtasks:
            try:
                if subtask.index > 1:
                    previous_subtasks = Subtask.objects.filter(task=task, index=(subtask.index -1))
                    all_previous_subtasks_finished = True
                    for previous_subtask in previous_subtasks:
                        if previous_subtask.status != 'finished': all_previous_subtasks_finished = False
                    if all_previous_subtasks_finished:
                        #We have a new subtask to submit
                        TaskClass = tools.get_task_class(task.task_type)
                        task_instance = TaskClass(task)
                        log.debug('Preparing new subtask %d' % (subtask.index))
                        prepared_subtask = task_instance.prepare_subtask(subtask.index)
                        #If this wasn't a local subtask, submit to condor  
                        if not subtask.local:
                            condor_tools.submit_task(prepared_subtask)
            except Exception, e:
                subtask.status = 'error'
                subtask.set_job_count()
                subtask.set_run_time()
                subtask.finish_time=  now()
                subtask.save()
                
                task.status = 'error'
                
                task.set_job_count()
                task.set_run_time()
                task.set_custom_field('error', str(e))
                task.finish_time = now()
                task.save()
                
                
        #Get the list of subtasks again
        task_subtasks = Subtask.objects.filter(task=task)
        finished = task_subtasks.filter(status='finished').order_by('index')
        if task_subtasks.count() == finished.count():
            task.status = 'finished'
            task.finish_time = now()
            log.debug('Task %s (user %s), all subtasks finished. Marking task as finished.' % (task.name, task.condor_pool.user.username))
            task.set_run_time()
            task.set_job_count()
            task.trim_condor_jobs()
            
            task.save()
            
        task.last_update_time=now()
        task.save()

def delete_task(task):
    #Mark the task as deleted, update the run time from any associated subtasks, remove the subtasks and associated condor jobs
    subtasks = task.subtask_set.all()
    for subtask in subtasks:
        subtask.set_job_count()
        subtask.set_run_time()
        jobs = subtask.condorjob_set.all()
        for job in jobs:
            job.delete()
    task.set_job_count()
    task.set_run_time()
    for subtask in subtasks:
        subtask.delete()    
    task.status = 'deleted'
    task.save()
    
def zip_up_task(task):
    """Zip up the task directory and return the filename
    """
    name = str(task.name).replace(' ', '_')
    filename = os.path.join(task.directory, name + '.tar.bz2')
    if not os.path.isfile(filename):
        tar = tarfile.open(name=filename, mode='w:bz2')
        tar.add(task.directory, name)
        tar.close()
    return filename