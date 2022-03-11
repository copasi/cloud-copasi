#!/usr/bin/env bash

# Set needed env variables, unless they are already set (e.g. via the Dockerfile)
# Both the condor and our own Python modules need to be seen (in addition to system site packages).
export CONDOR_CONFIG=${CONDOR_CONFIG:-'/home/cloudcopasi/condor/etc/condor_config'}
export PYTHONPATH=${PYTHONPATH:-'/home/cloudcopasi/condor/lib/python3:/home/cloudcopasi/cloud-copasi'}
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-'cloud_copasi.settings'}

# In case legacy Deployment instructions (not Docker), prepend local venv modules to PYTHONPATH . . .
[ -d 'venv' ] && source venv/bin/activate

# Start condor
. /home/cloudcopasi/condor/condor.sh &&
condor_master &

# temporary "fix" to mitigate db not being up before the webapp needs it
sleep 18 &&

# Run any migrations to update models and/or schema
if [ ! -f /home/cloudcopasi/cloud-copasi/web_interface/migrations/0001_initial.py ]
  then
    echo making migrations for web_interface
    python /home/cloudcopasi/cloud-copasi/manage.py makemigrations
fi

# Do we also have to wait for the db tables to be made?
sleep 18 &&

python /home/cloudcopasi/cloud-copasi/manage.py migrate &&

sleep 33 &&

# Start the daemon
python /home/cloudcopasi/cloud-copasi/cloud_copasi/background_daemon/cloud_copasi_daemon.py start #"$@"

# Run with uvicorn (instead of the Django test webserver)
python /home/cloudcopasi/cloud-copasi/manage.py uvicorn

# Start the server
python /home/cloudcopasi/cloud-copasi/manage.py runserver 0.0.0.0:8000
