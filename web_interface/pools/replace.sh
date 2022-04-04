#!/bin/bash
# Hasan Baig

SAMPLE_FILENAME='sample_slurm_submit.sh'
FILE_TO_TRANSFER='slurm_submit.sh'

ORIGINAL_PSTRING='PPPPPPPP'
NEW_PSTRING=$1

ORIGINAL_QSTRING='QQQQQQQQ'
NEW_QSTRING=$2

REMOTE_HOST=$3

cp $SAMPLE_FILENAME $FILE_TO_TRANSFER
sed -i "s/${ORIGINAL_PSTRING}/${NEW_PSTRING}/;s/${ORIGINAL_QSTRING}/${NEW_QSTRING}/" $FILE_TO_TRANSFER
scp -i ~/.ssh/bosco_key.rsa $FILE_TO_TRANSFER $REMOTE_HOST:bosco/glite/bin/

#scp $FILE_TO_TRANSFER $REMOTE_HOST:
