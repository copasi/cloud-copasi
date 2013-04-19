#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
import subprocess, re
import os.path, time

CONDOR_Q = '/usr/bin/condor_q'
CONDOR_SUBMIT = '/usr/bin/condor_submit'
CONDOR_RM = '/usr/bin/condor_rm'

def process_condor_q():
    condor_q_process = subprocess.Popen(CONDOR_Q, stdout=subprocess.PIPE)
    condor_q_output = condor_q_process.communicate()[0].splitlines()
    
    #Process the output using regexps. Example line is as follows:
    # ID      OWNER            SUBMITTED     RUN_TIME ST PRI SIZE CMD               
    #18756.0   ed              1/7  11:45   0+03:19:53 R  0   22.0 CopasiSE.$$(OpSys)
    condor_q=[]
    no_of_jobs = len(condor_q_output) - 6
    if no_of_jobs > 0:
        job_string = r'\s*(?P<id>\d+)\.0\s+(?P<owner>\S+)\s+(?P<sub_date>\S+)\s+(?P<sub_time>\S+)\s+(?P<run_time>\S+)\s+(?P<status>\w)\s+(?P<pri>\d+)\s+(?P<size>\S+)\s+(?P<cmd>\S+)'
        job_re = re.compile(job_string)
        for job_listing in condor_q_output:
            match = job_re.match(job_listing)
            if match:
                id = int(match.group('id'))
                owner = match.group('owner')
                sub_date = match.group('sub_date')
                sub_time = match.group('sub_time')
                run_time = match.group('run_time')
                status = match.group('status')
                pri = match.group('pri')
                size=match.group('size')
                cmd=match.group('cmd')
                
                condor_q.append((id,status))

    return condor_q

def condor_submit(condor_file):
    """Submit the .job file condor_file to the condor system using the condor_submit command"""
    #condor_file must be an absolute path to the condor job filename
    (directory, filename) = os.path.split(condor_file)
    
    p = subprocess.Popen([CONDOR_SUBMIT, condor_file],stdout=subprocess.PIPE, cwd=directory)
        
    process_output = p.communicate()[0]
    #Get condor_process number...
#    process_id = int(process_output.splitlines()[2].split()[5].strip('.'))
    #use a regular expression to parse the process output
    try:
        r=re.compile(r'[\s\S]*submitted to cluster (?P<id>\d+).*')
        process_id = int(r.match(process_output).group('id'))
    except:
        process_id = -1 #Return -1 if for some reason the submit failed
        #logging.exception('Failed to submit job')
    #TODO: Should we sleep here for a bit? 1s? 10s?
    time.sleep(0.5)
    return process_id

def condor_rm(queue_id):
    
    p = subprocess.Popen([CONDOR_RM, str(queue_id)])
    p.communicate()
    time.sleep(0.5)

