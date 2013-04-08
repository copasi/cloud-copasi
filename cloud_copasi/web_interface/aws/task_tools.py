#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from boto import s3, sqs
import json, s3_tools, os, sys
from cloud_copasi.web_interface.models import Task, CondorJob
from boto.s3.key import Key
from cloud_copasi.web_interface.aws import aws_tools
from boto.sqs.message import Message

def copy_to_bucket(filename, bucket, delete):
    key = Key(bucket)
    path, name = os.path.split(filename)
    key.name = name
    key.set_contents_from_filename(filename)
    if delete:
        os.remove(filename)
    return name

def store_to_outgoing_bucket(task, delete=True, copy_original_model=True):
    """Copy the files in the list to the outgoing bucket of the task. By default
    files will be deleted from the local drive after they have been copied over
    """
    assert isinstance(task, Task)
    
    s3_connection = s3_tools.create_s3_connection(task.condor_pool.vpc.access_key)
    bucket_name = task.get_outgoing_bucket_name()
    
    filepath, filename = os.path.split(task.original_model)
    
    #Create the bucket if it doesn't already exist?
    
    bucket = s3_connection.create_bucket(bucket_name)
    
    #Get a list of the condor jobs we're going to copy over
    #Filter jobs for only unsubmitted
    condor_jobs = CondorJob.objects.filter(task=task, queue_status='C')
    
    file_keys = []
    spec_keys = []
    
    if copy_original_model:
        key_name = copy_to_bucket(task.original_model, bucket, delete)
        
        #Update the filepathfield so that it now only points to a key name on s3
        task.original_model = key_name
        task.save()
        
    for condor_job in condor_jobs:
        model_key_name = copy_to_bucket(condor_job.copasi_file, bucket, delete)
        condor_job.copasi_file = model_key_name
        file_keys.append(model_key_name)
        
        spec_key_name = copy_to_bucket(condor_job.spec_file, bucket, delete)
        condor_job.spec_file = spec_key_name
        spec_keys.append(spec_key_name)
        
        condor_job.save()

    return file_keys, spec_keys
    
    #Delete the folder that contained the files
    if delete:
        #Delete the parent folder of the last file
        try:
            os.rmdir(filepath)
        except:
            #Most likely dir not empty
            pass
    
    
    return file_keys, spec_keys

def notify_new_task(task, file_key_names, spec_key_names):
    """Notify the pool queue that there is a new task to run
    """
    assert isinstance(task, Task)
    queue_name = task.condor_pool.get_queue_name()
    sqs_connection = aws_tools.create_sqs_connection(task.condor_pool.vpc.access_key)
    queue = sqs_connection.get_queue(queue_name)
    assert queue != None
    
    output = {}
    output['notify_type'] = 'new_task'
    output['bucket_name'] = task.get_outgoing_bucket_name()
    output['task_id'] = task.id
    output['file_keys'] = file_key_names
    output['spec_keys'] = spec_key_names
    
    condor_jobs = CondorJob.objects.filter(task=task).filter(queue_status='C')
    output_jobs = []
    for job in condor_jobs:
        output_jobs.append((job.id, job.spec_file))
    
    output['jobs'] = output_jobs

    json_output = json.dumps(output)
    message = Message()
    message.set_body(json_output)
    
    print >>sys.stderr, queue.write(message)
