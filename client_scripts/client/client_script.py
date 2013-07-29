#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
import boto
import boto.sqs
from boto.sqs import connection
import sys, json
import response, condor_tools, task_tools

def readline(path):
    return open(path, 'r').read().splitlines()[0]

aws_access_key = readline('/etc/cloud-config/aws_access_key')
aws_secret_key = readline('/etc/cloud-config/aws_secret_key')
pool_id = readline('/etc/cloud-config/pool_id')




def process_message(message, log):
    """Process an sqs message containing job information
    """
    
    assert isinstance(message, boto.sqs.message.Message)
    
    message_body = message.get_body()
    
    #Load the message as a json object
    data = json.loads(message_body)
    
    notify_type = data['notify_type']
    
    log.debug('Message type: %s' % notify_type)
    
    if notify_type == 'new_task':
        
        task_id = data['task_id']
        
        job_store = task_tools.submit_new_task(data, aws_access_key, aws_secret_key, log)
        
        responder = response.RegisterJobResponse(task_id)
        for job_id, queue_id in job_store:
            responder.add_condor_job(job_id, queue_id)
            print str(job_id), str(queue_id)
        
        outcome = responder.send_response()
        log.debug('Sent response. Outcome: %s' % outcome)

    elif notify_type == 'delete_jobs':
        print 'delete jobs'
        deleted_jobs = task_tools.delete_jobs(data['jobs'], data['folder'])
        responder = response.RegisterDeletedJobResponse(deleted_jobs)
        responder.send_response()
        
    elif notify_type == 'file_transfer':
        print 'file transfer'
        transferred_jobs = task_tools.transfer_files(data, aws_access_key, aws_secret_key)
        responder=response.RegisterTransferredFilesResponse(data['folder'], data['reason'], transferred_jobs)
        responder.send_response()
        
def run(log):
    #################################################
    # Read the queue to check for new job updates   #
    #################################################
    
    sqs_connection = connection.SQSConnection(aws_access_key_id=aws_access_key,
                                             aws_secret_access_key=aws_secret_key)


    queue_name = 'cloud-copasi-%s' % pool_id
    log.debug('Queue name : %s' % queue_name)
    
    
    queue = sqs_connection.get_queue(queue_name)

    log.debug('reading queue')
    message = queue.read()
    while message != None:
        try:
            #Go through all messages in the queue and process them
            #try:
                #process message
            log.debug('New message found. Processing...')
            process_message(message, log)
                
            queue.delete_message(message)

            #Reload the message
            message = queue.read()
        except Exception, e:
            log.error(str(e))
        
    ##############################################
    # Get the condor pool status and report back #
    ##############################################
    
    #TODO:Get actual status
    condor_q = condor_tools.process_condor_q()
    
    update_response =response.UpdateResponse()
    
    update_response.set_condor_jobs_from_q(condor_q)

    update_response.send_response()
    
if __name__ == '__main__':
    run()
