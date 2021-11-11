#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from cloud_copasi.web_interface.models import EC2Pool, Task
from cloud_copasi.web_interface.aws import ec2_tools

from logging import getLogger
from cloud_copasi.web_interface.pools import condor_tools
from cloud_copasi.web_interface.email import email_tools
import logging

#log = getLogger(__name__)
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

def refresh_all_ec2_pools():
    """Refresh all ec2 pools
    """
    check.debug('Refreshing all EC2 pools')
    pools = EC2Pool.objects.all() #Get all pools indiscriminately

    #added by HB
    #check.debug("@@@@@@@@@@@@@ List of pools (pool_tools.py) : ")
    #check.debug(pools)

    for ec2_pool in pools:
        try:
            ec2_tools.refresh_pool(ec2_pool)
        except Exception as e:
            log.exception(e)

def terminate_idle_pools():
    """Terminate any pool that doesn't have any more tasks running on it
    """

    ec2_pools = EC2Pool.objects.filter(auto_terminate=True)
    for ec2_pool in ec2_pools:
        try:
            copied_pools = EC2Pool.objects.filter(copy_of=ec2_pool)
            all_tasks = Task.objects.filter(condor_pool=ec2_pool) | Task.objects.filter(condor_pool__in=copied_pools)
            running_tasks = all_tasks.filter(status='running') | all_tasks.filter(status='new')
            if running_tasks.count() == 0 and all_tasks.count() > 0:

                pool_name = ec2_pool.name
                check.debug('Terminating pool %s since no other jobs running (auto terminate)' % pool_name)

                #Prune the tasks so that they are disassociated from the pool
                for task in all_tasks:
                    task.condor_pool = None
                    task.set_custom_field('condor_pool_name', pool_name)
                    task.save()

                if ec2_pool.get_pool_type() == 'ec2' and ec2_pool.copy_of == None:
                    error_list = []
                    #Remove the copied pools first
                    for copied_pool in copied_pools:
                        try:
                            copied_pool.delete()
                        except Exception as e:
                            log.exception(e)
                            error_list += ['Error deleting duplicate pool', str(e)]
                    #Remove from bosco
                    try:
                        condor_tools.remove_ec2_pool(ec2_pool)
                    except Exception as e:
                        log.exception(e)
                        error_list += ['Error removing pool from bosco', str(e)]
                    try:
                        email_tools.send_pool_auto_termination_email(ec2_pool)
                    except:
                        log.exception(e)
                    ec2_tools.terminate_pool(ec2_pool)

        except Exception as e:
            log.exception('Error terminating pool')
            log.exception(e)
