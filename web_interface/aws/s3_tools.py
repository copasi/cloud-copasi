#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from boto.s3.connection import S3Connection

def create_s3_connection(aws_access_key):
    """Create an s3 connection from the aws access key
    """
    
    s3_connection = S3Connection(aws_access_key.access_key_id, aws_access_key.secret_key)
    return s3_connection


