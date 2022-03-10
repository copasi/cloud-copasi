#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
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
timeout ${timeout}s ${copasi_binary} --nologo --home . load_balancing_1.cps  &>/dev/null
end=$$((`date +%s`*1000+`date +%-N`/1000000))
difference=`expr $$end - $$start`

#Echo the elapsed time in seconds
echo -n "1 "
echo "scale=4; $$difference / 1000" | bc
#if the difference is greater than 10 seconds (10000ms)
if [ $$difference -gt 10000 ]; then
exit 0
fi

#Run the same test but with 10 repeats

#record time in milliseconds
start=$$((`date +%s`*1000+`date +%-N`/1000000))
timeout ${timeout}s ${copasi_binary} --nologo --home . ${copasi_file_10}  &>/dev/null
end=$$((`date +%s`*1000+`date +%-N`/1000000))
difference=`expr $$end - $$start`
#Echo the elapsed time in seconds
echo -n "10 "
echo "scale=4; $$difference / 1000" | bc
if [ $$difference -gt 10000 ]; then
exit 0
fi
#Run the same test but with 100 repeats
#record time in milliseconds
start=$$((`date +%s`*1000+`date +%-N`/1000000))
timeout ${timeout}s ${copasi_binary} --nologo --home . ${copasi_file_100}  &>/dev/null
end=$$((`date +%s`*1000+`date +%-N`/1000000))
difference=`expr $$end - $$start`
#Echo the elapsed time in seconds
echo -n "100 "
echo "scale=4; $$difference / 1000" | bc
if [ $$difference -gt 10000 ]; then
exit 0
fi

#Run the same test but with 1000 repeats
#record time in milliseconds
start=$$((`date +%s`*1000+`date +%-N`/1000000))
timeout ${timeout}s ${copasi_binary} --nologo --home . ${copasi_file_1000}  &>/dev/null
end=$$((`date +%s`*1000+`date +%-N`/1000000))
difference=`expr $$end - $$start`
echo -n "1000 "
echo "scale=4; $$difference / 1000" | bc
exit 0
"""