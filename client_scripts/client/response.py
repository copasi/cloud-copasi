#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
import json, urllib2

URL='http://127.0.0.1:8000'
REGISTER_JOB='/api/register_job/'
UPDATE_STATUS='/api/register_job/'

class JSONResponder(object):
    
    def send_response(self, address, data):
        assert isinstance(data, dict)
        
        request = urllib2.Request(address)
        request.add_header('Content-Type', 'application/json')
        response=urllib2.urlopen(request, json.dumps(data))
        
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
    
    def __init__(self,server_url, pool_id, secret_key, job_id):
        self.server_url = server_url
        self.pool_id=pool_id
        self.secret_key=secret_key
        self.job_id=job_id
        
    def add_condor_job(self, condor_job_id, queue_id):
        self.condor_jobs.append((condor_job_id, queue_id))
        #todo:how do we link these to specific jobs? probably depends on the job s3 file
        
    def send_response(self):
        #Get the response address
        address = 'http://' + self.server_url + REGISTER_JOB
        #Construct a dict containing the response data
        output={}
        
        output['pool_id']=self.pool_id
        output['secret_key']=self.secret_key
        output['job_id']=self.job_id
        
        output['condor_jobs'] = self.condor_jobs
        
        return super(RegisterJobResponse, self).send_response(address, output)


class UpdateResponse(JSONResponder):
    condor_jobs=[]
    
    def __init__(self, server_url, pool_id, secret_key):
        self.server_url=server_url
        self.pool_id=pool_id
        self.secret_key=secret_key
        
    def add_condor_job(self, queue_id, status):
        self.condor_jobs.append([queue_id, status])
        #todo:how do we link these to specific jobs? probably depends on the job s3 file
        
    def set_condor_jobs_from_q(self, condor_q):
        self.condor_jobs = condor_q
        
    def send_response(self):
        #Get the response address
        address = 'http://' + self.server_url + UPDATE_STATUS
        #Construct a dict containing the response data
        output={}
        
        output['pool_id']=self.pool_id
        output['secret_key']=self.secret_key
        
        output['condor_jobs'] = self.condor_jobs
        
        return super(UpdateResponse, self).send_response(address, output)

