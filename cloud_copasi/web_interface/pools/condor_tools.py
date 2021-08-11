#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
import subprocess, re, os
import os.path, time
from cloud_copasi import settings
import logging
from cloud_copasi.web_interface.models import EC2Pool, Subtask, CondorJob
from cloud_copasi.web_interface.pools import condor_log_tools
import datetime
#from django.utils.timezone import now
from django.utils import timezone   #added by HB

log = logging.getLogger(__name__)
########### following lines are set by HB for debugging
logging.basicConfig(
        filename='/home/cloudcopasi/log/debug.log',
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%m/%d/%y %I:%M:%S %p',
        level=logging.DEBUG
    )
check = logging.getLogger(__name__)
######################################################

CONDOR_Q = 'condor_q'
CONDOR_SUBMIT = 'condor_submit'
CONDOR_RM = 'condor_rm'
BOSCO_CLUSTER = 'bosco_cluster'

#Set up the Bosco environment variables (equivalent to bosco_setenv)
os_env = os.environ.copy()

env={}
#bosco_path = os.path.join(settings.BOSCO_DIR, 'bin') + ':' + os.path.join(settings.BOSCO_DIR, 'sbin')
#env['PATH'] = bosco_path + ':' + os_env.get('PATH', '')
#env['CONDOR_CONFIG'] = os.path.join(settings.BOSCO_DIR, 'etc/condor_config')
#env['HOME'] = settings.HOME_DIR

#the upper lines of code are commented out by HB to adjust the bosco path for condor v9.1.2 below
bosco_path = os.path.join(settings.BOSCO_DIR, 'usr/bin') + ':' + os.path.join(settings.BOSCO_DIR, 'usr/sbin')
env['PATH'] = bosco_path + ':' + os_env.get('PATH', '')
env['CONDOR_CONFIG'] = os.path.join(settings.BOSCO_DIR, 'etc/condor_config')
env['HOME'] = settings.HOME_DIR


###Custom env options
if hasattr(settings, 'BOSCO_CUSTOM_ENV'):
    #env = dict(env.items() + settings.BOSCO_CUSTOM_ENV.items())
    env = env.copy()
    env.update(settings.BOSCO_CUSTOM_ENV)



def run_bosco_command(command, error=False, cwd=None, shell=False, text=None): #added by HB: text=None.
    #added by HB for debugging
    check.debug('bosco_path: %s' %bosco_path)
    check.debug("***** Running following bosco command now *****")
    check.debug(command)

    #check.debug('env: %s' %env)
    #added by HB: text=text.
    check.debug('@ 12. run_bosco() in condor_tools.py -------|')
    process = subprocess.Popen(command, shell=shell, env=env,  stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, text=text)

    output = process.communicate()

    check.debug("============ OUTPUT: ")
    check.debug(output)

    if not error: return output[0].splitlines()
    else: return (output[0].splitlines(), output[1].splitlines(), process.returncode)

#defintion added by HB to overwrite slurm_submit file on a remote server
def transfer_file(slurm_partition, slurm_qos, address):
    SCRIPT='./replace.sh'

    if (slurm_partition == ''):
        slurm_partition='general'

    if (slurm_qos == ''):
        slurm_qos='general'

    check.debug("============ slurm inputs modified: ")
    check.debug(slurm_partition)
    check.debug(slurm_qos)

    check.debug("Address: ")
    check.debug(address)
    check.debug("$$$$ Current Working Directory: ")
    check.debug(os.getcwd())
    cwd_old = os.getcwd()
    chng_cwd = cwd_old + '/cloud-copasi/cloud_copasi/web_interface/pools'
    os.chdir(chng_cwd)

    check.debug("$$$$ Changed Working Directory: ")
    check.debug(os.getcwd())

    command=[SCRIPT, slurm_partition, slurm_qos, address]
    process=subprocess.Popen(command,stdout=subprocess.PIPE, shell=False)
    output=process.communicate()
    os.chdir(cwd_old)

    check.debug("$$$$ CWD changed back to: ")
    check.debug(os.getcwd())

#the last two arguments in the following function are added by HB
def add_bosco_pool(platform, address, keypair, pool_type='condor', slurm_partition=' ', slurm_qos=' '):

    command = 'eval `ssh-agent`; ssh-add ' + keypair + '; '

    #command += BOSCO_CLUSTER + ' --platform %s --add %s %s;' % (platform, address, pool_type)
    #The above line is modified as follows by HB to remove --platform switch for condor v9.1.2 to download the correct condor version on remote host
    command += BOSCO_CLUSTER + ' --add %s %s;' % (address, pool_type)

    #The following line is modified by HB
    #command += './' + BOSCO_CLUSTER + ' --platform %s --add %s %s;' % (platform, address, pool_type)

    command += 'kill $SSH_AGENT_PID;'

    #added by HB
    check.debug("Executing the adding bosco pool command: ")
    check.debug(command)
    #####

    output = run_bosco_command(command, error=True, shell=True)

    log.debug(output)

    #added by HB
    check.debug("============ slurm inputs received: ")
    check.debug(slurm_partition)
    check.debug(slurm_qos)

    transfer_file(slurm_partition, slurm_qos, address)
    return output

def remove_bosco_pool(address):

    log.debug('Removing pool %s' %address)
    output = run_bosco_command([BOSCO_CLUSTER, '--remove', address], error=True)
    log.debug('Response:')
    log.debug(output)

    #log.debug('Removing pool from ssh known_hosts')
    #process = subprocess.Popen(['ssh-keygen', '-R', address], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    #output = process.communicate()
    #log.debug(output)

    return output

def test_bosco_pool(address):
    check.debug('Testing bosco cluster %s', address)

    command = [BOSCO_CLUSTER, '--test', address]

    #added by HB
    #command = BOSCO_CLUSTER + ' --test %s;' %address

    #added by HB for debugging
    check.debug('Bosco Test Command: %s', command)

    #output =  run_bosco_command(command, error=True, shell=True)
    output =  run_bosco_command(command, error=True)

    check.debug('Test response:')
    #check.debug(output)
    check.debug(output[0])
    check.debug('Errors:')
    check.debug(output[1])
    check.debug('Exit status')
    check.debug(output[2])

    return output


def add_ec2_pool(ec2_pool):
    """Add an EC2 pool to bosco
    """
    assert isinstance(ec2_pool, EC2Pool)

    address = str(ec2_pool.address)

    platform = 'DEB6' #Ubuntu-based server
    pool_type = 'condor' #Condor scheduler
    keypair = ec2_pool.key_pair.path

    log.debug('Adding EC2 pool to bosco')

    output = add_bosco_pool(platform, address, keypair, pool_type)
    return output

def remove_ec2_pool(ec2_pool):
    address = str(ec2_pool.address)
    return remove_bosco_pool(address)

def condor_submit(condor_file):
    """Submit the .job file condor_file to the condor system using the condor_submit command"""
    #condor_file must be an absolute path to the condor job filename
    (directory, filename) = os.path.split(condor_file)

    #added by HB
    check.debug('@ 11. condor_submit() in condor_tools.py -------|')

    check.debug("@ 11a. ---> Condor Job running: %s" %filename)
    #check.debug(filename)
    output, error, exit_status = run_bosco_command([CONDOR_SUBMIT, condor_file], error=True, cwd=directory)
    check.debug('@ 11b. ---> Console output of condor job submission: ')
    check.info(output)

    #Get condor_process number...
    #process_id = int(process_output.splitlines()[2].split()[5].strip('.'))
    #use a regular expression to parse the process output
    process_output = output[-1] #We're only interested in the last line

    try:
        #assert exit_status == 0
        r=re.compile(r'^(?P<n>\d+) job\(s\) submitted to cluster (?P<cluster>\d+).*', re.DOTALL)
        #log.debug('r= ',r)
	#added by HB
        #process_output = process_output.decode('utf-8')
        check.debug('@ 11c. ---> Process output: ')
        check.debug(process_output)

        PO_to_string = process_output.decode('utf-8')

        try:
            #number_of_jobs = int(r.match(process_output).group('n'))

            #added by HB
            #number_of_jobs = int(re.match(r'(^[0-9]*)', PO_to_string).group(1))
            number_of_jobs = int(r.match(PO_to_string).group('n'))

        except AttributeError:
            #number_of_jobs = int(r.match(process_output))
            #added by HB
            #number_of_jobs = int(re.match(r'(^[0-9]*)', PO_to_string))
            number_of_jobs = int(r.match(PO_to_string))

        #cluster_id = int(r.match(process_output).group('cluster'))
	#added by HB
        #cluster_id = int(re.search(r'([0-9]*)\.$' ,PO_to_string).group(1))
        cluster_id = int(r.match(PO_to_string).group('cluster'))

    except Exception as e:
        log.exception('Failed to submit job')
        log.exception(e)
        log.exception(output)
        log.exception(error)
        log.exception(exit_status)
        raise e
    return (cluster_id, number_of_jobs)






def submit_task(subtask):
    """Submit the subtask to the pool. Create all necessary CondorJobs, and update their status.
    """

    assert isinstance(subtask, Subtask)
    assert subtask.spec_file != ''

    spec_file_path = os.path.join(subtask.task.directory, subtask.spec_file)
    #added by HB
    check.debug('@ 10. submit_task() in condor_tools.py -------|')  #added by HB
    check.debug("@ 10a. ----> spec file path: %s" %spec_file_path)
    #check.debug(spec_file_path)

    cluster_id, number_of_jobs = condor_submit(spec_file_path)

    check.debug('@ 10b. ----> Cluster id: %d' % cluster_id)
    check.debug('@ 10c. ----> Number_of_jobs: %d' % number_of_jobs)


    #Check to see if std_output_file, std_err_file, log_file or job_output were specified by the subtask
    #If not use the defualt values

    if subtask.get_custom_field('std_output_file') != None:
        std_output_file_n = subtask.get_custom_field('std_output_file')
    else:
        std_output_file_n = 'auto_copasi_%d.%%d.cps.out' % subtask.index

    if subtask.get_custom_field('std_err_file') != None:
        std_err_file_n = subtask.get_custom_field('std_err_file')
    else:
        std_err_file_n = 'auto_copasi_%d.%%d.cps.err' % subtask.index

    if subtask.get_custom_field('log_file') != None:
        log_file_n = subtask.get_custom_field('log_file')
    else:
        log_file_n = 'auto_copasi_%d.%%d.cps.log' % subtask.index


    if subtask.get_custom_field('job_output') != None:
        job_output_n = subtask.get_custom_field('job_output')
    else:
        job_output_n = 'output_%d.%%d.txt' % subtask.index

    if subtask.get_custom_field('copasi_file') != None:
        copasi_model_filename_n = subtask.get_custom_field('copasi_file')
    else:
        copasi_model_filename_n = 'auto_copasi_%d.%%d.cps' % subtask.index


    subtask.cluster_id=cluster_id
    for n in range(number_of_jobs):

        try:
            std_output_file = std_output_file_n % n
        except:
            std_output_file = std_output_file_n
        try:
            std_err_file = std_err_file_n % n
        except:
            std_err_file = std_err_file_n
        try:
            log_file = log_file_n % n
        except:
            log_file = log_file_n
        try:
            copasi_model_filename = copasi_model_filename_n % n
        except:
            copasi_model_filename = copasi_model_filename_n
        try:
            job_output = job_output_n % n
        except:
            job_output = job_output_n

        job = CondorJob(subtask=subtask,
                        std_output_file = std_output_file,
                        std_error_file = std_err_file,
                        log_file = log_file,
                        job_output = job_output,
                        status = 'I',
                        process_id = n,
                        run_time = 0.0,
                        copasi_file = copasi_model_filename,
                        )
        job.save()

    subtask.status='running'
    #subtask.start_time = now()
    #above line is modified by HB for debugging timing issues
    subtask.start_time = timezone.localtime()

    subtask.save()
    #added by HB

def remove_task(subtask):
    """Call condor_rm on the condor jobs belonging to a subtask
    """
    assert isinstance(subtask, Subtask)
    if subtask.status == 'running' or subtask.status == 'error':
        #log.debug('Removing subtask with cluster id %s from condor_q' % subtask.cluster_id)
        try:
            output, error, exit_status = run_bosco_command([CONDOR_RM, str(subtask.cluster_id)], error=True)
            #assert exit_status == 0
            check.debug("subtask removed")    #added by HB
            return output, error, exit_status

        except:
            log.debug('Error removing subtask from condor_q')
            try:
                log.debug('%s, %s, %s' % (output, error, exit_status))
            except:
                pass

        try:
            for job in subtask.condorjob_set.all():
                job.delete()
        except Exception as e:
            log.exception(e)
    else:
        return (None, None, None)

def read_condor_q():

    """Execute the condor_q command and process the output
    Returns a list of tuples of the form (cluster_id, process_id, status)
    where status is a single lettter, e.g. I, R, H, X
    """
    #added by HB
    check.debug("**** RUN by Background Script **** read_condor_q() in condor_tools.py -------|")

    #condor_q_output, error, exit_status = run_bosco_command([CONDOR_Q], error=True)
    #above line is modified by HB as follows:
    condor_q_output, error, exit_status = run_bosco_command([CONDOR_Q, '-nobatch'], error=True, text=True)

    #added by HB
    #temp_command = CONDOR_Q + ' -nobatch'
    #condor_q_nobatch = run_bosco_command(temp_command, error=True, shell=True)
    check.debug("@@@@@ condor_q_output:")
    check.debug(condor_q_output)
    check.debug(' ')
    #check.debug("$$$$$ condor_q -nobatch output: $$$$$")
    #check.debug(condor_q_nobatch)


    #following line is commented out by HB
    #assert exit_status == 0

    #Process the output using regexps. Example line is as follows:
    # ID      OWNER            SUBMITTED     RUN_TIME ST PRI SIZE CMD
    #18756.0   ed              1/7  11:45   0+03:19:53 R  0   22.0 CopasiSE.$$(OpSys)
    condor_q=[]
    #no_of_jobs = len(condor_q_output) - 6    #added by HB. Why -6?
    no_of_jobs = len(condor_q_output) - 8    #value modified by HB to discard unnecessary lines
    check.debug("@@@@@ no_of_jobs: %d" %no_of_jobs)
    #check.debug(no_of_jobs)

    #added by HB
    #converting the condor_q_output to string format
    #condor_q_output_str = condor_q_output.decode('utf-8')
    #check.debug('@@@@@ condor_q_output in STRING format: ')
    #check.debug(condor_q_output_str)

    if no_of_jobs > 0:
        check.debug("_*_*_*_*_ if block executed _*_*_*_*_")
        job_string = r'\s*(?P<cluster_id>\d+)\.(?P<process_id>\d+)\s+(?P<owner>\S+)\s+(?P<sub_date>\S+)\s+(?P<sub_time>\S+)\s+(?P<run_time>\S+)\s+(?P<status>\w)\s+(?P<pri>\d+)\s+(?P<size>\S+)\s+(?P<cmd>\S+)'
        job_re = re.compile(job_string)
        #added by HB. following for-loop command is modified to process the condor_q_output in string format.
        #for job_listing in condor_q_output_str:
        for job_listing in condor_q_output:
            check.debug(" ******* job_listing: %s" %job_listing)
            match = job_re.match(job_listing)
            check.debug(" ******* match: %s" %match)    #added by HB
    
            if match:
                cluster_id = int(match.group('cluster_id'))
                check.debug(" ******* cluster_id: %d" %cluster_id)  #added by HB
                process_id = int(match.group('process_id'))
                check.debug(" ******* process_id: %d" %process_id)  #added by HB

                owner = match.group('owner')
                check.debug(" ******* owner: %s" %owner)  #added by HB
                sub_date = match.group('sub_date')
                check.debug(" ******* sub_date: %s" %sub_date)  #added by HB
                sub_time = match.group('sub_time')
                check.debug(" ******* sub_time: %s" %sub_time)  #added by HB
                run_time = match.group('run_time')
                check.debug(" ******* run_time: %s" %run_time)  #added by HB
                status = match.group('status')
                check.debug(" ******* status: %s" %status)  #added by HB
                pri = match.group('pri')
                check.debug(" ******* pri: %s" %pri)  #added by HB
                size=match.group('size')
                check.debug(" ******* size: %s" %size)  #added by HB
                cmd=match.group('cmd')
                check.debug(" ******* cmd: %s" %cmd)  #added by HB

                condor_q.append((cluster_id, process_id,status))


    #added by HB
    check.debug("$@$@$@ condor_q: ")
    check.debug(condor_q)

    return condor_q

def process_condor_q(user=None, subtask=None):
    """Process the output of the condor q and updates the status of condor jobs as necessary
    If specified we can narrow down to a specific user or subtask

    Note: this method only updates the status of CondorJob objects. It does not update any upstream subtask or task changes. this is performed in task_tools
    """
    #added by HB
    check.debug("*********Entered in process_condor_q definition ***********")

    #Next, get a list of all condor jobs we think are still running
    #Status will be 'I', 'R', 'H'

    #added by HB
    check.debug("subtask: ")
    check.debug(subtask)

    condor_jobs = CondorJob.objects.filter(status='I') | CondorJob.objects.filter(status='R') | CondorJob.objects.filter(status='H')

    if user:
        condor_jobs = condor_jobs.filter(subtask__task__user=user)
    if subtask:
        condor_jobs = condor_jobs.filter(subtask=subtask)

    #added by HB
    check.debug("condor_jobs: ")
    check.debug(condor_jobs)

    if len(condor_jobs) == 0:
        check.debug('No jobs marked as running. Not checking condor_q')
        pass

    else:
        check.debug('Reading condor_q')
        condor_q = read_condor_q()


        for job in condor_jobs:
            in_q = False
            for cluster_id, process_id, status in condor_q:
                if (status != 'C' and status != 'X') and process_id == job.process_id and cluster_id == job.subtask.cluster_id:
                    #Skip if state == 'C' -- means complete, so just assume not in the queue
                    in_q = True
                    job.status = status
                    job.save()
            if not in_q:
                #If not in the queue, then the job must have finished running. Change the status accordingly
                #TODO: At some point we need to validate the job based on the log file
                check.debug('Job %d.%d (Task %s) not in queue. Checking log' % (job.subtask.cluster_id, job.process_id, job.subtask.task.name))

                log_path = os.path.join(job.subtask.task.directory, job.log_file)
                #added by HB
                check.debug("@$@$@$@ log_path: ")
                check.debug(log_path)

                condor_log = condor_log_tools.Log(log_path)

                #added by HB
                check.debug("@$@$@$@ condor_log: ")
                check.debug(condor_log)

                #added by HB
                check.debug("@$@$@$@ Job.Status: ")
                check.debug(job.status)

                if condor_log.has_terminated:
                    if condor_log.termination_status == 0:
                        check.debug('Log indicates normal termination. Checking output files exist')

                        if job.job_output != '' and job.job_output != None:
                            output_filename = os.path.join(job.subtask.task.directory, job.job_output)

                            if os.path.isfile(output_filename):
                                try:
                                    assert os.path.getsize(output_filename) > 0
                                    try:
                                        run_time =  condor_log.running_time_in_days
                                        check.debug(" -*-*-*- run_time: ")
                                        check.debug(run_time)
                                        job.run_time = run_time
                                        run_time_minutes = run_time * 24 * 60
                                    except:
                                        run_time_minutes = None
                                    log.debug('Job output exists and is nonempty. Marking job as finished with run time %s minutes' % run_time_minutes)
                                    job.status = 'F'
                                except:
                                    log.debug('Job output exists but is empty. Leaving status as running')
                            else:
                                log.debug('Output file does not exist. Leaving status as running')

                        else:
                            log.debug('Job has no output specified. Assuming job has finished.')
                            job.status = 'F'
                    else:
                        log.debug('Log indicates abnormal termination. Marking job as error')
                        job.status = 'E'
                else:
                    #log.debug('Log indicates job not terminated. Leaving status as running')
                    pass
                job.save()

def cancel_task(task):
    #TODO: implement this method
    return
