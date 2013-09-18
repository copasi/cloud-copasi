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
log = getLogger(__name__)

def refresh_all_ec2_pools():
    """Refresh all ec2 pools
    """
    log.debug('Refreshing all EC2 pools')
    pools = EC2Pool.objects.all() #Get all pools indiscriminately
    
    for ec2_pool in pools:
        try:
            ec2_tools.refresh_pool(ec2_pool)
        except Exception, e:
            log.exception(e)

def terminate_idle_pools():
    """Terminate any pool that doesn't have any more tasks running on it
    """
    
    ec2_pools = EC2Pool.objects.filter(auto_terminate=True)
    for ec2_pool in ec2_pools:
        try:
            all_tasks = Task.objects.filter(condor_pool=ec2_pool)
            running_tasks = all_tasks.objects.filter(status='running') | all_tasks.objects.filter(status='new')
            if running_tasks.count() == 0 and all_tasks.count() > 0:
                pool_name = ec2_pool.name
                log.debug('Terminating pool %s since no other jobs running (auto terminate)' % pool_name)
                ec2_tools.terminate_pool(ec2_pool)
        except Exception, e:
            log.exception('Error terminating pool')
            log.exception(e)