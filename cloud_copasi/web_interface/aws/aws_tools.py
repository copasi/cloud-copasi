#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from boto.vpc import VPCConnection
from boto.ec2 import EC2Connection
from boto.exception import BotoServerError
from boto.sqs.connection import SQSConnection

def create_connections(key):
    vpc_connection = VPCConnection(key.access_key_id, key.secret_key)
    ec2_connection = EC2Connection(key.access_key_id, key.secret_key)
    return (vpc_connection, ec2_connection)

def process_errors(error_list):
    """Process the list of errors such that any boto errors are flattened"""
    output=[]
    for error in error_list:
        if isinstance(error, BotoServerError):
            for boto_error in error.errors:
                output.append(boto_error)
        else:
            output.append(error)
    return output

def create_sqs_connection(key):
    return SQSConnection(key.access_key_id, key.secret_key)
