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
#import response
from .response import *

from cloud_copasi import settings

import logging



from cloud_copasi.web_interface.pools import condor_tools, task_tools
from cloud_copasi.background_daemon.tools import pool_tools

########### following lines are set by HB for debugging
logging.basicConfig(
        filename='/home/cloudcopasi/log/debug.log',
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%m/%d/%y %I:%M:%S %p',
        level=logging.DEBUG
    )
######################################################


if __name__ == '__main__':
    #log = logging.getLogger('cloud_copasi.background_daemon.tools.background_script')
    check = logging.getLogger('cloud_copasi.background_daemon.tools.background_script')   #added by HB
else:
    #log = logging.getLogger(__name__)
    check = logging.getLogger(__name__)   #added by HB



def run():
    check.debug("_________________ run() function runs _________________")
    try:
        pool_tools.refresh_all_ec2_pools()
    except Exception as e:
        log.exception(e)
    
    check.debug('@@@@@ running process_condor_q by background_script $$$$$$$$$$')
    condor_tools.process_condor_q()
    
    check.debug('@@@@@ running update_tasks() by background_script $$$$$$$$$$')
    task_tools.update_tasks()

    try:
        pool_tools.terminate_idle_pools()
    except Exception as e:
        #log.exception(e)
        check.exception(e)   #added by HB

    check.debug('Finished background script')

if __name__ == '__main__':
    run()
