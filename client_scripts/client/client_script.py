#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
import boto
from boto.sqs import connection
import sys
from client_scripts.client import response, condor_tools, task_tools

def readline(path):
    return open(path, 'r').read().splitlines()[0]

def main():
    
    #Open the files storing the variables we need
    server_url = readline('/etc/cloud-config/server_url')
    pool_id = int(readline('/etc/cloud-config/pool_id'))
    secret_key = readline('/etc/cloud-config/secret_key')
    aws_access_key = readline('/etc/cloud-config/aws_access_key')
    aws_secret_key = readline('/etc/cloud-config/aws_secret_key')
    
    
    #################################################
    # Read the queue to check for new job updates   #
    #################################################
    sqs_connection = connection.SQSConnection(aws_access_key_id=aws_access_key,
                                             aws_secret_access_key=aws_secret_key)
    
    queue_name = 'cloud-copasi-pool-' + str(pool_id)
    
    queue = sqs_connection.get_queue(queue_name)
    
    message = queue.read()
    while message != None:
        #Go through all messages in the queue and process them
        try:
            #process message
            #
            message.delete()
        except:
            pass
        #Reload the message
        message = queue.read()
        
    ##############################################
    # Get the condor pool status and report back #
    ##############################################
    
    #TODO:Get actual status
    condor_q = condor_tools.process_condor_q()
    
    update_response =response.UpdateResponse(server_url, pool_id, secret_key)
    
    update_response.set_condor_jobs_from_q(condor_q)

    print update_response.send_response()
    
if __name__ == '__main__':
    main()
