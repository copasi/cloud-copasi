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
