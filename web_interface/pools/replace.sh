#!/bin/bash
# replace.sh - replace slurm_local_submit_attributes.sh on a slurm submit node
# usage: replace.sh partition qos remote_host
# remote_host needs to be the usual bosco pool address: user@submit.node.edu
#
# Written by Hasan Baig and Pedro Mendes, 2021-2022

# currently, condor version is not needed, uncomment here and if/else below if needed
# get the condor version, inlcuding major and minor (3rd level not needed as of now)
#VERSION=`~/condor/bin/condor_version | head -n 1 | sed 's/.*\([0-9]\+\.[0-9]\+\.[0-9]\+\).*/\1/'`
#MAJOR=$(expr match "$VERSION" '^\([0-9]\+\).*')
#MINOR=$(expr match "$VERSION" '^[0-9]\+\.\([0-9]\+\).*')

# temporary file to hold the slurm partition and qos, will be transferred to submit node
FILETMP="/tmp/slurm_local_submit_attributes.$RANDOM"

# add SBATCH commands to file
echo "#!/bin/bash" > $FILETMP
echo "echo \"#SBATCH -p $1\"" >> $FILETMP
echo "echo \"#SBATCH -q $2\"" >> $FILETMP

# make it executable
chmod a+x $FILETMP

# get the submit node address
REMOTE_HOST=$3

# default file location
DESTINATION_FILE="bosco/glite/etc/blahp/slurm_local_submit_attributes.sh"

# check condor version and adjust location of file this does not seem to 
# be needed for the time being; if a later version of condor changes the
# location of slurm_local_submit_attributes.sh then use this construct to
# act appropriately
#if [[ $MAJOR -ge 9 ]]
#then
#  if [[ $MINOR -gt 7 ]]
#  then
#      DESTINATION_FILE="bosco/glite/etc/blahp/slurm_local_submit_attributes.sh"
#  fi
#fi

# do the transfer, using the bosco_key.rsa
scp -i ~/.ssh/bosco_key.rsa $FILETMP $REMOTE_HOST:$DESTINATION_FILE

# clean up
rm $DESTINATION_FILE

# done
