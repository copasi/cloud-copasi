#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from shutil import rmtree
from boto.s3.connection import S3Connection
from boto.s3.bucket import Bucket
from boto.s3.key import Key
import os
import condor_tools, response

def submit_new_task(task_data, aws_access_key, aws_secret_key):
    """Submit a new task to the condor pool
    """
    task_id = task_data['task_id']
    
    bucket_name = task_data['bucket_name']
    
    s3_connection = S3Connection(aws_access_key, aws_secret_key)
    bucket = s3_connection.get_bucket(bucket_name)
    assert isinstance(bucket, Bucket)
    
    
    #First create the working directory
    
    working_dir = os.path.join(os.path.expanduser('~'), 'condor_files', str(task_id))
    
    #Does the path already exist? If so delete whatever's in there
    if os.path.exists(working_dir):
        rmtree(working_dir)
    
    os.makedirs(working_dir)
    
    #First copy over the necessary files
    
    #Files
    file_keys = task_data['file_keys']
    
    #Also get the spec files
    for job_id, spec_file in task_data['jobs']:
        file_keys.append(spec_file)
    
    #Copy all the filenames over from S3:    
    for key_name in file_keys:
        key = bucket.get_key(key_name)
        assert isinstance(key, Key)
        
        filename = os.path.join(working_dir, key_name)
        key.get_contents_to_filename(filename)
    
    #Submit all the spec files to condor
    #Construct a data store containing tuples:(job_id, condor_q_id)
    job_store = []
    for job_id, spec_file in task_data['jobs']:
        filename = os.path.join(working_dir, spec_file)
        queue_id = condor_tools.condor_submit(filename)
        job_store.append((job_id, queue_id))
    
    
    
    return job_store

def delete_jobs(job_list, folder):
    """Delete the following jobs from the Condor pool"""
    deleted_jobs = []
    for job_id in job_list:
        try:
            condor_tools.condor_rm(job_id)
            deleted_jobs.append(job_id)
        except:
            print 'couldnt delete job %d' %job_id
    working_dir = os.path.join(os.path.expanduser('~'), 'condor_files', str(folder))
    
    if len(deleted_jobs) == len(job_list):
        try:
            rmtree(working_dir)
        except:
            print 'couldnt delete task folder'

    return deleted_jobs