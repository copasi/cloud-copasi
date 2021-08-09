#!/usr/bin/env bash

# Fill in the appropriate locations forPYTHONPATH and
# PYTHONHOME below.

export PYTHONPATH=$PYTHONPATH:/home/cloudcopasi/cloud-copasi
#export PYTHONPATH=/home/cloudcopasi/cloud-copasi/cloud_copasi
export PYTHONHOME=/home/cloudcopasi/cloud-copasi/venv
export DJANGO_SETTINGS_MODULE=cloud_copasi.settings

# First start bosco
#source /home/cloudcopasi/bosco/bosco_setenv
#bosco_start

#above two lines are modified by HB for Condor v9.1.2 as follows
. /home/cloudcopasi/condor/condor.sh
condor_master

# The daemon needs to use the virtual environment
source /home/cloudcopasi/cloud-copasi/venv/bin/activate

# Start the daemon
#python /home/cloudcopasi/cloud-copasi/cloud_copasi/background_daemon/cloud_copasi_daemon.py "$@"

#modified above line as follows by HB
python /home/cloudcopasi/cloud-copasi/cloud_copasi/background_daemon/cloud_copasi_daemon.py "$@"
