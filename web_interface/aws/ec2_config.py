#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
#EC2 machine image details
AMI_IMAGE_ID = 'ami-0ae2ae4fb7cd587c4'

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
          ('t1.micro','t1.micro (1 vCPUs, 0.5GB - Free tier eligible)'),
          ('t2.micro','t2.micro (1 vCPUs, 1GB - Free tier eligible)'),
          ('t2.small','t2.small (1 vCPUs, 2GB)'),
          ('t2.medium','t2.medium (2 vCPUs, 2GB)'),
          ('t2.large','t2.large (2 vCPUs, 8GB)'),

          
          ('a1.medium', 'a1.medium (1 vCPUs, 2GB)'),
          ('a1.large','a1.large (2 vCPUs, 4GB)'),
          ('a1.xlarge','a1.xlarge (4 vCPUs, 8GB)'),
          ('a1.2xlarge','a1.2xlarge (8 vCPUs, 16GB)'),

          ('m4.large', 'm4.large (2 vCPUs, 8GB, Moderate Network Performance)'),
          ('m4.xlarge', 'm4.xlarge (4 vCPUs, 16GB, High Network Performance)'),
          
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
