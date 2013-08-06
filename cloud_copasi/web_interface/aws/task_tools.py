#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from boto import s3, sqs
import json, s3_tools, os, sys
from cloud_copasi.web_interface.models import Task, CondorJob, Subtask
from boto.s3.key import Key
from cloud_copasi.web_interface.aws import aws_tools
from boto.sqs.message import Message
from cloud_copasi.web_interface.task_plugins import tools

#Note: 31/7/2013, rewritten to support only local task submission with Bosco


def update_task(task):
    
    task_class = tools.get_task_class(task.task_type)
    
    subtasks = Subtask.objects.filter(task=task)
    
    #Are there any subtasks with status 'new'?
    
    