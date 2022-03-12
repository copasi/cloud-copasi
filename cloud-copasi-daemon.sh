#!/usr/bin/env bash

export PYTHONPATH=$PYTHONPATH:/home/cloudcopasi/cloud-copasi
export DJANGO_SETTINGS_MODULE=cloud_copasi.settings


# Set the appropriate condor environment variables
# (dynamically determined by the condor intaller).
. /home/cloudcopasi/condor/condor.sh
# Start the condor cluster
# TODO: This seems to start worker slots on this web server. Do we really want all that?
condor_master

# Give the daemon access to needed Python dependendies
# if they have been installed in a Python virtual
# environment named "venv" (per "Deployment" instructions).
export PYTHONHOME=/home/cloudcopasi/cloud-copasi/venv
source /home/cloudcopasi/cloud-copasi/venv/bin/activate

# Run the daemon.
python /home/cloudcopasi/cloud-copasi/cloud_copasi/background_daemon/cloud_copasi_daemon.py "${1:-start}"
