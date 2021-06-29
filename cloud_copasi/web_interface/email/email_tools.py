#-------------------------------------------------------------------------------
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#
# Contributors:
#     Edward Kent - initial API and implementation
#-------------------------------------------------------------------------------
# Django settings for cc_scratch project.

from django.core.mail import send_mail
from django.urls import reverse_lazy
from cloud_copasi import settings
from cloud_copasi.web_interface.models import EC2Pool, Task
from logging import getLogger

log = getLogger(__name__)

message_header = """Dear %s,

"""

message_footer = """
------------
This message was sent automatically by Cloud-COPASI. To manage your email preferences, visit your account at %s
"""

def send_message(user, notify_type, subject, message_body):

    #Check to see if we're supposed to send emails for this user. If we're not then return already
    if hasattr(user, 'profile'):
        if user.profile.task_emails == False and notify_type=='task':
            return
        elif user.profile.pool_emails == False and notify_type == 'pool':
            return

    #And check we have an email address set for the user
    if user.email == None or user.email == '':
        return
    check.debug('Sending email')
    if user.first_name:
        name = user.first_name
    else:
        name = user.username
    header = message_header % name

    message = header + message_body + (message_footer % 'http://' + settings.HOST + str(reverse_lazy('my_account_profile')))

    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

def send_pool_auto_termination_email(ec2_pool):
    assert isinstance(ec2_pool, EC2Pool)

    message_body = """The EC2 compute pool %s has been terminated automatically since all running tasks have completed.
""" % ec2_pool.name

    subject = 'Cloud-COPASI: EC2 pool terminated (%s)' % ec2_pool.name

    send_message(ec2_pool.user, 'pool', subject, message_body)


def send_task_completion_email(task):
    assert isinstance(task, Task)


    if task.status == 'finished':
        message_body = """The task %s finished successfully.
You can view the results by visiting %s
""" % (task.name, 'http://' + settings.HOST + str(reverse_lazy('task_details', kwargs={'task_id':task.id})))
        subject = 'Cloud-COPASI: Task completed successfully (%s)'% task.name

    elif task.status == 'error':
        message_body = """The task %s encountered an error.
You can view the task details by visiting %s
""" % (task.name, 'http://' + settings.HOST + str(reverse_lazy('task_details', kwargs={'task_id':task.id})))
        subject = 'Cloud-COPASI: Task encountered error (%s)'% task.name
    else:
        return

    send_message(task.user, 'task', subject, message_body)

def send_task_cancellation_email(task):
    assert isinstance(task, Task)

    if task.status == 'cancelled':
        message_body = """The task %s has been cancelled. If this action was not expected, check whether the compute pool the task was running on has been removed.
""" % task.name
        subject = 'Cloud-COPASI: task cancelled (%s)' % task.name

        send_message(task.user, 'task', subject, message_body)
