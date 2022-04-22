#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2022- Hasan Baig.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from web_interface.task_plugins.base import BaseTask, BaseTaskForm
from web_interface.models import Task, CondorJob, CondorPool
from web_interface.models import Subtask
from django.forms import Form
from django import forms
from cloud_copasi import settings
from cloud_copasi.copasi.model import CopasiModel_BasiCO
from web_interface.task_plugins.plugins.parameter_estimation_repeat.copasi_model import PLCopasiModel_BasiCO # Use the task-specific copasi model in this directory
import os, math
import logging
from django.http.response import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from cloud_copasi.condor import condor_spec
from string import Template
from web_interface.task_plugins import load_balancing
import re
import datetime
#from django.utils.timezone import now
from django.utils import timezone #added by HB

log = logging.getLogger(__name__)
slog = logging.getLogger("special")

os.environ['HOME'] = settings.STORAGE_DIR #This needs to be set to a writable directory
import matplotlib
matplotlib.use('Agg') #Use this so matplotlib can be used on a headless server. Otherwise requires DISPLAY env variable to be set.
import matplotlib.pyplot as plt
from matplotlib.pyplot import annotate

internal_type = ('profile_likelihood', 'Profile Likelihood')

class TaskForm(BaseTaskForm):
    #Any extra fields for the task submission form
    parameter_estimation_data = forms.FileField(required=True, help_text='Select either a single data file, or if more than one data file is required, upload a .zip file containing multiple data files.')

class TaskPlugin(BaseTask:

    subtasks = 2

    def __init__(self, task):
        self.use_load_balancing = not task.get_custom_field('skip_load_balancing_step')

        if self.use_load_balancing:
            self.subtasks = 3
        else:
            self.subtasks = 2
            task.set_custom_field('repeats_per_job', 1)
            task.save()

        super(TaskPlugin, self).__init__(task)

        #added by HB
        slog.debug("---------> self.directory")
        slog.debug(self.task.directory)
        slog.debug("---------> self.task.original_model")
        slog.debug(self.task.original_model)

        slog.debug("+++++++++++ Running BasiCO implementation.")
        self.copasi_model = PLCopasiModel_BasiCO(os.path.join(self.task.directory, self.task.original_model))

    def validate(self):
        #TODO:Abstract this to a new COPASI class in this plugin package
        valid_result = self.copasi_model.is_valid('PL')
        slog.debug(valid_result)
        return valid_result
