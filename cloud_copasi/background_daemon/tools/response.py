#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
import json, urllib
import sys
from cloud_copasi import settings

#URLs
REGISTER_JOB='/api/register_job/'
UPDATE_STATUS='/api/update_status/'
REGISTER_DELETED_JOBS = '/api/register_deleted_jobs/'
REGISTER_TRANSFERRED_FILES = '/api/register_transferred_files/'
REMOTE_LOGGING_UPDATE ='/api/remote_logging_update/'


def readline(path):
    return open(path, 'r').read().splitlines()[0]

#Open the files storing the variables we need
server_url = settings.HOST
pool_id = None
secret_key = None


class JSONResponder(object):

    def send_response(self, address, data):

        url = 'http://' + server_url + address
        assert isinstance(data, dict)

        data['pool_id']=pool_id
        data['secret_key']=secret_key


        request = urllib.Request(url)
        request.add_header('Content-Type', 'application/json')
        response=urllib.urlopen(request, json.dumps(data))

        assert response.info().getheaders('content-type') == ['application/json']
        response_data=json.loads(response.read())

        assert response.getcode() == 201
        assert response_data['status'] == 'created'

        return True


class RegisterJobResponse(JSONResponder):
    """Class to represent the response we will send back to the server detailing
    the condor queue ids of the condor jobs
    """

    condor_jobs=[]

    def __init__(self, job_id):
        self.job_id=job_id

    def add_condor_job(self, condor_job_id, queue_id):
        self.condor_jobs.append((condor_job_id, queue_id))

    def send_response(self):
        #Get the response address
        address = REGISTER_JOB
        #Construct a dict containing the response data
        output={}

        output['job_id']=self.job_id

        output['condor_jobs'] = self.condor_jobs

        return super(RegisterJobResponse, self).send_response(address, output)


class UpdateResponse(JSONResponder):
    condor_jobs=[]

    def __init__(self):
        pass

    def add_condor_job(self, queue_id, status):
        self.condor_jobs.append([queue_id, status])

    def set_condor_jobs_from_q(self, condor_q):
        self.condor_jobs = condor_q

    def send_response(self):
        #Get the response address
        address = UPDATE_STATUS
        #Construct a dict containing the response data
        output={}


        output['condor_jobs'] = self.condor_jobs

        return super(UpdateResponse, self).send_response(address, output)

class RegisterDeletedJobResponse(JSONResponder):
    condor_jobs=[]

    def __init__(self, job_list):
        self.job_list = job_list



    def send_response(self):
        #Get the response address
        address = REGISTER_DELETED_JOBS
        #Construct a dict containing the response data
        output={}


        output['job_list'] = self.job_list

        return super(RegisterDeletedJobResponse, self).send_response(address, output)

class RegisterTransferredFilesResponse(JSONResponder):
    condor_jobs=[]

    def __init__(self, task_uuid, reason, file_list):
        self.file_list = file_list
        self.task_uuid = task_uuid
        self.reason=reason


    def send_response(self):
        #Get the response address
        address =  REGISTER_TRANSFERRED_FILES
        #Construct a dict containing the response data
        output={}

        output['task_uuid']=self.task_uuid
        output['reason']=self.reason
        output['file_list'] = self.file_list

        return super(RegisterTransferredFilesResponse, self).send_response(address, output)

class RemoteLoggingResponse(JSONResponder):

    def __init__(self, message_list):

        self.message_list = message_list

    def send_response(self):
        #Get the response address
        address = REMOTE_LOGGING_UPDATE
        #Construct a dict containing the response data
        output={}

        output['message_list']=self.message_list

        return super(RemoteLoggingResponse, self).send_response(address, output)
