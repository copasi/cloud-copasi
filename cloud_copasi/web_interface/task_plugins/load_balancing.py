
#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html

#Adapted from Condor-COPSAI
#code.google.com/p/condor-copasi


#This file contains the outline used for creating the load balancing script

load_balancing_string = """#!/bin/bash
#record time in milliseconds
start=$$((`date +%s`*1000+`date +%-N`/1000000))
timeout ${timeout}s ${copasi_binary} --nologo --home . ${copasi_file}  &>/dev/null
end=$$((`date +%s`*1000+`date +%-N`/1000000))
difference= `expr $$end - $$start`
#Echo the elapsed time in seconds
echo "scale=4; $$difference / 1000" | bc
"""

