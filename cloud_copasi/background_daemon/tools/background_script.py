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
import response

from cloud_copasi import settings

import logging



from cloud_copasi.web_interface.pools import condor_tools, task_tools
from cloud_copasi.background_daemon.tools import pool_tools

if __name__ == '__main__':
    log = logging.getLogger('cloud_copasi.background_daemon.tools.background_script')
else:
    log = logging.getLogger(__name__)


        
def run():
    try:
        pool_tools.refresh_all_ec2_pools()
    except Exception, e:
        log.exception(e)
        
    condor_tools.process_condor_q()
    
    task_tools.update_tasks()
    
    try:
        pool_tools.terminate_idle_pools()
    except Exception, e:
        log.exception(e)
    
    log.debug('Finished background script')
if __name__ == '__main__':
    run()
