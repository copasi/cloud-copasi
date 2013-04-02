from boto import s3, sqs
import json, s3_tools, os
from models import Task, CondorJob
from boto.s3.key import Key
from web_interface.aws import aws_tools

def store_to_outgoing_bucket(task, file_list, delete=True):
    """Copy the files in the list to the outgoing bucket of the task. By default
    files will be deleted from the local drive after they have been copied over
    """
    assert isinstance(task, Task)
    s3_connection = s3_tools.create_s3_connection(task.condor_pool.vpc.access_key)
    bucket_name = task.get_outgoing_bucket_name()
    
    #Create the bucket if it doesn't already exist?
    
    bucket = s3_connection.create_bucket(bucket_name)
    
    condor_jobs = CondorJob.objects.filter(task=task)
        
    key_names = []
    #Copy the files over
    for filename in file_list:
        key=Key(bucket)
        path, name= os.path.split(filename)
        key.name = name
        key.set_contents_from_filename(filename)
        
        key_names.append(name)
        
        if delete:
            os.remove(filename)

    #Copy the condor spec files over too. Don't append key names this time.
    #Edit the condor job spec files so that they only point to the key name, not
    #the full file path.
    for job in condor_jobs:
        filename = job.spec_file
        key=Key(bucket)
        path, name= os.path.split(filename)
        key.name = name
        key.set_contents_from_filename(filename)
        
        if delete:
            os.remove(filename)

        job.spec_file = name
        job.save()
    
    #Delete the folder that contained the files
    if delete and len(file_list)>0:
        #Delete the parent folder of the last file
        try:
            os.rmdir(path)
        except:
            #Most likely dir not empty
            pass
    
    
    return key_names
def notify_new_task(task, key_names):
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
    output['file_keys'] = key_names
    
    condor_jobs = CondorJob.objects.filter(task=task)
    output_jobs = []
    for job in condor_jobs:
        output_jobs.append(job.id, job.spec_file)
    
    output['jobs'] = output_jobs

    json_output = json.dumps(output)
    
    queue.write(json_output)