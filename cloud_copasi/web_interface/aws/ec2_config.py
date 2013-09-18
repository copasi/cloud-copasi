#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
MASTER_LAUNCH_STRING = """#!/bin/bash
/opt/condor_config/master_config.sh"""
#5 args
# - server_url
# - pool_id
# - secret_key
# - aws_key
# - aws_secret_key

WORKER_LAUNCH_STRING = """#!/bin/bash
/opt/condor_config/worker_config.sh %s"""


EC2_TYPE_CHOICES =(
          ('t1.micro','t1.micro (<2 ECU, 1 Core, 613MB (Free tier eligible))'),

          ('m1.small','m1.small (1 ECU, 1 Core, 1.7GB)'),
          ('m1.medium', 'm1.medium (2 ECUs, 1 Core, 3.7GB)'),
          ('m1.large','m1.large (4 ECUs, 2 Cores, 7.5GB)'),
          ('m1.xlarge','m1.xlarge (8 ECUs, 4 Cores, 15GB)'),

          #('m3.xlarge', 'm3.xlarge (13 ECUs, 4 Cores, 15GB)'),
          #('m3.2xlarge', 'm3.2xlarge (26 ECUs, 8 Cores, 30GB)'),
          
          ('m2.xlarge','m2.xlarge (6.5 ECUs, 2 Cores, 17.1GB)'),
          ('m2.2xlarge','m2.2xlarge (13 ECUs, 4 Cores, 34.2GB)'),
          ('m2.4xlarge','m2.4xlarge (26 ECUs, 8 Cores, 68.4GB)'),

          #('c1.medium','c1.medium (5ECUs, 2 Cores, 1.7GB)'),
          #('c1.xlarge','c1.xlarge (20ECUs, 8 Cores, 7GB)'),
          
          #('hs1.8xlarge','hs1.8xlarge (35ECUs, 16 Cores, 117GB)'),
          )

#===============================================================================
# Autoscale parameters
#===============================================================================

###Downscale parameters using cloudwatch alarms:

#Average CPU utilization percentage. <= this, instances will be terminated
DOWNSCALE_CPU_THRESHOLD = 10
#The time period monitored. Unless detailed monitoring is enabled, in seconds
DONWSCALE_CPU_PERIOD = 300
#Number of consecutive periods the cpu threshold must pass before instances are terminated
DOWNSCALE_CPU_EVALUATION_PERIODS = 4