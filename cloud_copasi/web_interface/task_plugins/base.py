#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from cloud_copasi.web_interface.models import CondorJob, Subtask, BoscoPool,EC2Pool
from django import forms
from cloud_copasi.web_interface import form_tools
#from cloud_copasi.web_interface.task_plugins import tools
from cloud_copasi.web_interface.models import CondorPool
import itertools
import logging

log = logging.getLogger(__name__)
########### following lines are set by HB for debugging
logging.basicConfig(
        filename='/home/cloudcopasi/log/debug.log',
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%m/%d/%y %I:%M:%S %p',
        level=logging.DEBUG
    )
check = logging.getLogger(__name__)
######################################################

#===============================================================================
# Base task plugin structure
#===============================================================================

class BaseTaskForm(forms.Form):
    name = forms.CharField()
    #Populate the task type field with an initial empty string option
    task_type = forms.ChoiceField()
    #access_key = form_tools.NameChoiceField(queryset=None, initial=0)
    model_file = forms.FileField()
    compute_pool = form_tools.PoolChoiceField(queryset=None, initial=0)


    def __init__(self, user, task_types,  *args, **kwargs):
        super(BaseTaskForm, self).__init__(*args, **kwargs)
        self.user = user
        self.fields['task_type'].choices = [('', '------------')] + task_types
        #access_keys = AWSAccessKey.objects.filter(user=self.user).filter(vpc__isnull=False)
        #self.fields['access_key'].queryset = access_keys

        ec2_pools = EC2Pool.objects.filter(user = user).filter(vpc__isnull=False)
        ec2_pool_ids = [pool.pk for pool in ec2_pools]

        shared_ec2_pools = EC2Pool.objects.filter(user=user).filter(copy_of__isnull=False)
        shared_ec2_pool_ids = [pool.pk for pool in shared_ec2_pools]

        bosco_pools = BoscoPool.objects.filter(user=user)
        bosco_pool_ids = [pool.pk for pool in bosco_pools]

        condor_pools = CondorPool.objects.filter(pk__in=ec2_pool_ids + shared_ec2_pool_ids + bosco_pool_ids)

        self.fields['compute_pool'].queryset = condor_pools



class BaseTask(object):

    internal_name = ('base', 'Base task')

    #The number of subtasks this task is split into
    subtasks=0

    def __init__(self, task):
        self.task = task

    def validate(self):
        return True

    def prepare_subtask(self, index=0):
        """Prepare a particular subtask to run
        """

        #Ensure the correct files are on the system
        return []

    def initialize_subtasks(self):
        pass

    def create_new_subtask(self, subtask_type, local=False):
        #Get a count of the number of existing subtasks
        subtask_count = len(Subtask.objects.filter(task=self.task))

        subtask =  Subtask()
        subtask.task = self.task
        subtask.index = subtask_count + 1
        subtask.type = subtask_type
        subtask.status = 'waiting'
        subtask.active = False
        subtask.local = local
        subtask.save()

    def get_subtask(self, index):
        #Get a particular subtask by index
        subtasks = Subtask.objects.filter(task=self.task)
        #added by HB
        check.debug("Value of index: %d" %index)
        if index == 2 or index == 3:
            check.debug("Subtask got: ")
            check.debug(subtasks)

        return subtasks.get(index=index)

    def get_results_view_data(self, request):
        """Return a dict with any data to be used in the task results view page
        """
        return {}

    def get_template_name(self, name):
        """Return the full path of the template with given name
        """
        check.debug("task_type: ")
        check.debug(self.task.task_type)
        check.debug("name: %s" %name)
        return '%s/%s.html' % (self.task.task_type, name)

    def get_results_view_template_name(self, request):
        """Return a string with the path of the results view page
        """

        return self.get_template_name('results_view')
