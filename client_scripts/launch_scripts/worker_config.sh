#!/bin/bash
#Script to configure Condor as a Worker
#Locate in /opt/condor_config

#Use the first argument as the condor host
CONDOR_HOST=$1

#Kill any running Condor
service condor stop

#Add an entry for the current hostname
IP="$(ifconfig eth0 | sed -n '/inet /{s/.*addr://;s/ .*//;p}')"
echo "$IP $(hostname)" >> /etc/hosts

#Use the Condor host config file
ln -s /etc/condor/condor_config.worker /etc/condor/condor_config.local

#Set the instance hostname as the Condor
sed -i "s:^\(CONDOR_HOST\s*=\s*\).*$:\1$CONDOR_HOST:" /etc/condor/condor_config.local

#Set the domain correctly
#DOMAIN=`hostname -d`
#sed -i "s:<domain>:$DOMAIN:" /etc/condor/condor_config.local

service condor start