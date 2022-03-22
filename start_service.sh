#!/usr/bin/env bash

# workaround to give the database time to start
sleep 21

# I think these may be needed for the Django stuff here.
export PYTHONPATH=$PYTHONPATH:/home/cloudcopasi/cloud-copasi
export DJANGO_SETTINGS_MODULE=cloud_copasi.settings
source /home/cloudcopasi/cloud-copasi/venv/bin/activate

# Run the migrations to populate the database
python3 /home/cloudcopasi/cloud-copasi/manage.py migrate

# workaround to give the migrations a change to finish
sleep 27

# Start the Cloud Copasi daemon
/home/cloudcopasi/cloud-copasi/cloud-copasi-daemon.sh start

# give the daemon a chance to start
sleep 9

# Start the web server
python3 /home/cloudcopasi/cloud-copasi/manage.py runserver "${1:-0.0.0.0}:${2:-8000}"
