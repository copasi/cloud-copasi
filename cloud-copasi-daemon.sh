#!/usr/bin/env bash

# Set needed env variables, unless they are already set (e.g. via the Dockerfile)
# Both the condor and our own Python modules need to be seen (in addition to system site packages).
export CONDOR_CONFIG=${CONDOR_CONFIG:-'/home/cloudcopasi/condor/etc/condor_config'}
export PYTHONPATH=${PYTHONPATH:-'/home/cloudcopasi/condor/lib/python3:/home/cloudcopasi/cloud-copasi'}
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-'cloud_copasi.settings'}

# In case legacy Deployment instructions (not Docker), prepend local venv modules to PYTHONPATH . . .
[ -d 'venv' ] && source venv/bin/activate

# Start condor
. /home/cloudcopasi/condor/condor.sh &
condor_master &

# Start the daemon
python /home/cloudcopasi/cloud-copasi/cloud_copasi/background_daemon/cloud_copasi_daemon.py "$@"

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
