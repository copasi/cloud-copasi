#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html

#Simple script to delete a bucket and all that's in it

from boto.s3.connection import S3Connection
from boto.s3.bucket import Bucket
import sys
from boto.s3.key import Key


aws_key = sys.argv[1]
secret_key = sys.argv[2]
bucket_name = sys.argv[3]

con = S3Connection(aws_key, secret_key)
assert isinstance(con, S3Connection)
bucket = con.get_bucket(bucket_name)

assert isinstance(bucket, Bucket)

keys=bucket.get_all_keys()

for key in keys:
    assert isinstance(key, Key)
    key.delete()
    
bucket.delete()
