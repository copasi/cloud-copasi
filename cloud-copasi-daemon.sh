#!/usr/bin/env bash

# Fill in the appropriate locations forPYTHONPATH and
# PYTHONHOME below.

export PYTHONPATH=$PYTHONPATH:/home/cloudcopasi/cloud-copasi
export PYTHONHOME=/home/cloudcopasi/cloud-copasi/venv
export DJANGO_SETTINGS_MODULE=cloud_copasi.settings

python /home/cloudcopasi/cloud-copasi/cloud_copasi/background_daemon/cloud_copasi_daemon.py $@
