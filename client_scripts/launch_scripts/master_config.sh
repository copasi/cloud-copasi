#!/bin/bash

#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
#Locate in /opt/condor_config
#Script to configure Condor as a Master

SERVER_URL=$1
POOL_ID=$2
SECRET_KEY=$3
AWS_ACCESS_KEY=$4
AWS_SECRET_KEY=$5

#Write the server url, pool id and secret key to files in /etc/
echo $SERVER_URL > /etc/cloud-config/server_url
echo $POOL_ID > /etc/cloud-config/pool_id
echo $SECRET_KEY > /etc/cloud-config/secret_key
echo $AWS_ACCESS_KEY > /etc/cloud-config/aws_access_key
echo $AWS_SECRET_KEY > /etc/cloud-config/aws_secret_key

#Kill any running Condor
service condor stop

#Add an entry for the current hostname
IP="$(ifconfig eth0 | sed -n '/inet /{s/.*addr://;s/ .*//;p}')"
echo "$IP $(hostname)" >> /etc/hosts


#Use the Condor host config file
ln -s /etc/condor/condor_config.master /etc/condor/condor_config.local

#Set the instance hostname as the Condor
#sed -i "s:^\(CONDOR_HOST\s*=\s*\).*$:\1$CONDOR_HOST:" /etc/condor/condor_config.local

#Set the domain correctly
#DOMAIN=`hostname -d`
#sed -i "s:<domain>:$DOMAIN:" /etc/condor/condor_config.local

service condor start
