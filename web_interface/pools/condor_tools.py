#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
import subprocess, re, os
import os.path, time
import shutil
from cloud_copasi import settings
import logging
from web_interface.models import EC2Pool, Subtask, CondorJob
from web_interface.pools import condor_log_tools
import datetime
#from django.utils.timezone import now
from django.utils import timezone   #added by HB

log = logging.getLogger(__name__)
slog = logging.getLogger("special")
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

    process = subprocess.Popen(command, shell=shell, env=env,  stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, text=text)

    output = process.communicate()

    if not error: return output[0].splitlines()
    else: return (output[0].splitlines(), output[1].splitlines(), process.returncode)

#defintion added by HB to overwrite slurm_submit file on a remote server
def transfer_file(slurm_partition, slurm_qos, address):
    SCRIPT='./replace.sh'

    if (slurm_partition == ''):
        slurm_partition='general'

    if (slurm_qos == ''):
        slurm_qos='general'

    log.debug("============ slurm inputs modified: ")
    log.debug(slurm_partition)
    log.debug(slurm_qos)

    log.debug("Address: ")
    log.debug(address)
    log.debug("$$$$ Current Working Directory: ")
    log.debug(os.getcwd())
    cwd_old = os.getcwd()
    chng_cwd = cwd_old + '/cloud-copasi/cloud_copasi/web_interface/pools'
    os.chdir(chng_cwd)

    log.debug("$$$$ Changed Working Directory: ")
    log.debug(os.getcwd())

    command=[SCRIPT, slurm_partition, slurm_qos, address]
    process=subprocess.Popen(command,stdout=subprocess.PIPE, shell=False)
    output=process.communicate()
    os.chdir(cwd_old)

    log.debug("$$$$ CWD changed back to: ")
    log.debug(os.getcwd())

#the last two arguments in the following function are added by HB
def add_bosco_pool(platform, address, keypair, pool_type='condor', slurm_partition=' ', slurm_qos=' '):

    command = 'eval `ssh-agent`; ssh-add ' + keypair + '; '

    #command += BOSCO_CLUSTER + ' --platform %s --add %s %s;' % (platform, address, pool_type)
    #The above line is modified as follows by HB to remove --platform switch for condor v9.1.2 to download the correct condor version on remote host
    command += BOSCO_CLUSTER + ' --add %s %s;' % (address, pool_type)

    command += 'kill $SSH_AGENT_PID;'


    output = run_bosco_command(command, error=True, shell=True)

    log.debug(output)

    #added by HB
    log.debug("============ slurm inputs received: ")
    log.debug(slurm_partition)
    log.debug(slurm_qos)

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
    log.debug('Testing bosco cluster %s', address)

    command = [BOSCO_CLUSTER, '--test', address]

    #output =  run_bosco_command(command, error=True, shell=True)
    output =  run_bosco_command(command, error=True)

    log.debug('Test response:')
    #log.debug(output)
    log.debug(output[0])
    log.debug('Errors:')
    log.debug(output[1])
    log.debug('Exit status')
    log.debug(output[2])

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
    log.debug('submitting job to pool')
    output, error, exit_status = run_bosco_command([CONDOR_SUBMIT, condor_file], error=True, cwd=directory)

    #Get condor_process number...
    #process_id = int(process_output.splitlines()[2].split()[5].strip('.'))
    #use a regular expression to parse the process output
    process_output = output[-1] #We're only interested in the last line

    try:
        #assert exit_status == 0
        r=re.compile(r'^(?P<n>\d+) job\(s\) submitted to cluster (?P<cluster>\d+).*', re.DOTALL)
        #log.debug('r= ',r)

        PO_to_string = process_output.decode('utf-8')

        try:
            number_of_jobs = int(r.match(PO_to_string).group('n'))

        except AttributeError:
            number_of_jobs = int(r.match(PO_to_string))

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

    cluster_id, number_of_jobs = condor_submit(spec_file_path)

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
    subtask.start_time = timezone.localtime()

    subtask.save()


def remove_task(subtask):
    """Call condor_rm on the condor jobs belonging to a subtask
    """
    assert isinstance(subtask, Subtask)
    if subtask.status == 'running' or subtask.status == 'error':
        #log.debug('Removing subtask with cluster id %s from condor_q' % subtask.cluster_id)
        try:
            output, error, exit_status = run_bosco_command([CONDOR_RM, str(subtask.cluster_id)], error=True)
            #assert exit_status == 0
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
    condor_q_output, error, exit_status = run_bosco_command([CONDOR_Q, '-nobatch'], error=True, text=True)


    #Process the output using regexps. Example line is as follows:
    # ID      OWNER            SUBMITTED     RUN_TIME ST PRI SIZE CMD
    #18756.0   ed              1/7  11:45   0+03:19:53 R  0   22.0 CopasiSE.$$(OpSys)
    condor_q=[]

    no_of_jobs = len(condor_q_output) - 8    #value updated to 8 to discard unnecessary lines in htcondor v9.x

    if no_of_jobs > 0:
        job_string = r'\s*(?P<cluster_id>\d+)\.(?P<process_id>\d+)\s+(?P<owner>\S+)\s+(?P<sub_date>\S+)\s+(?P<sub_time>\S+)\s+(?P<run_time>\S+)\s+(?P<status>\w)\s+(?P<pri>\d+)\s+(?P<size>\S+)\s+(?P<cmd>\S+)'
        job_re = re.compile(job_string)
        #added by HB. following for-loop command is modified to process the condor_q_output in string format.
        #for job_listing in condor_q_output_str:
        for job_listing in condor_q_output:
            match = job_re.match(job_listing)

            if match:
                cluster_id = int(match.group('cluster_id'))
                process_id = int(match.group('process_id'))
                owner = match.group('owner')
                sub_date = match.group('sub_date')
                sub_time = match.group('sub_time')
                run_time = match.group('run_time')
                status = match.group('status')
                pri = match.group('pri')
                size=match.group('size')
                cmd=match.group('cmd')

                condor_q.append((cluster_id, process_id,status))

    return condor_q

def process_condor_q(user=None, subtask=None):
    """Process the output of the condor q and updates the status of condor jobs as necessary
    If specified we can narrow down to a specific user or subtask

    Note: this method only updates the status of CondorJob objects. It does not update any upstream subtask or task changes. this is performed in task_tools
    """
    slog.debug("Reading if condor job is either I, R or H")
    condor_jobs = CondorJob.objects.filter(status='I') | CondorJob.objects.filter(status='R') | CondorJob.objects.filter(status='H')

    if user:
        condor_jobs = condor_jobs.filter(subtask__task__user=user)
    if subtask:
        condor_jobs = condor_jobs.filter(subtask=subtask)


    if len(condor_jobs) == 0:
        log.debug('No jobs marked as running. Not checking condor_q')
        pass

    else:
        slog.debug('Reading condor_q: ')
        condor_q = read_condor_q()
        slog.debug(condor_q)

        for job in condor_jobs:
            in_q = False
            for cluster_id, process_id, status in condor_q:
                if (status != 'C' and status != 'X') and process_id == job.process_id and cluster_id == job.subtask.cluster_id:
                    #Skip if state == 'C' -- means complete, so just assume not in the queue
                    # slog.debug("Job %d.%d has status %s, and it is in queue." % (job.subtask.cluster_id, job.process_id, job.status))
                    in_q = True
                    job.status = status
                    job.save()
            if not in_q:
                #If not in the queue, then the job must have finished running. Change the status accordingly
                #TODO: At some point we need to validate the job based on the log file
                #log.debug('Job %d.%d (Task %s) not in queue. Checking log' % (job.subtask.cluster_id, job.process_id, job.subtask.task.name))

                slog.debug("Job %d.%d has status %s, and it is NOT in queue." % (job.subtask.cluster_id, job.process_id, job.status))
                slog.debug("Checking the Job %d.%d log at:" % (job.subtask.cluster_id, job.process_id))

                log_path = os.path.join(job.subtask.task.directory, job.log_file)

                slog.debug(log_path)
                
                #add try except block here. 
                condor_log = condor_log_tools.Log(log_path)

                slog.debug("This runs")
                log.debug("This goes in cloud-copasi.log file")

                if condor_log.has_terminated:
                    slog.debug("has_terminated runs")
                    if condor_log.termination_status == 0:
                        slog.debug('Log indicates normal termination. Checking output files exist')

                        if job.job_output != '' and job.job_output != None:
                            output_filename = os.path.join(job.subtask.task.directory, job.job_output)

                            if os.path.isfile(output_filename):
                                try:
                                    assert os.path.getsize(output_filename) > 0
                                    try:
                                        run_time =  condor_log.running_time_in_days
                                        log.debug(" -*-*-*- run_time: ")
                                        log.debug(run_time)
                                        job.run_time = run_time
                                        run_time_minutes = run_time * 24 * 60
                                    except:
                                        run_time_minutes = None
                                    slog.debug('Job output exists and is nonempty. Marking job as finished with run time %s minutes' % run_time_minutes)
                                    job.status = 'F'
                                except:
                                    slog.debug('Job output exists but is empty. Leaving status as running')
                            else:
                                slog.debug('Output file does not exist. Leaving status as running')

                        else:
                            slog.debug('Job has no output specified. Assuming job has finished.')
                            job.status = 'F'
                    else:
                        slog.debug('Log indicates abnormal termination. Marking job as error')
                        job.status = 'E'


                # elif condor_log.job_aborted:
                #     slog.debug("Job %d has aborted, and must be deleted." %job.subtask.cluster_id)
                #     slog.debug("Directory to be deleted: ")
                #     slog.debug(job.subtask.task.directory)
                #     # shutil.rmtree(dir)

                else:
                    #log.debug('Log indicates job not terminated. Leaving status as running')
                    slog.debug("Log does not have a TERMINATED statement.")
                    pass
                job.save()

def cancel_task(task):
    #TODO: implement this method
    return
