#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
import subprocess, re


CONDOR_Q = '/usr/bin/condor_q'

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
