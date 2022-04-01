#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
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
from web_interface.task_plugins.plugins.raw_mode.copasi_model import RWCopasiModel_BasiCO
import os, math
import logging
from django.http.response import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from cloud_copasi.condor import condor_spec
from web_interface.task_plugins import load_balancing
from string import Template
import re
import datetime
#from django.utils.timezone import now
from django.utils import timezone #added by HB
# import time #added by HB to debug Local subtask time

log = logging.getLogger(__name__)
slog = logging.getLogger("special")

os.environ['HOME'] = settings.STORAGE_DIR #This needs to be set to a writable directory
import matplotlib

matplotlib.use('Agg') #Use this so matplotlib can be used on a headless server. Otherwise requires DISPLAY env variable to be set.
import matplotlib.pyplot as plt
import io #added by HB
from matplotlib.pyplot import annotate

internal_type = ('raw_mode', 'Raw mode')

class TaskForm(BaseTaskForm):
    #Any extra fields for the task submission form
    repeats = forms.IntegerField(required=True, min_value=1, help_text='The number of repeats to perform.')
    optional_data = forms.FileField(required=False, label='Optional data files', help_text='Select either a single data file, or if more than one data file is required, upload a .zip file containing multiple data files.')
    raw_mode_args = forms.RegexField(max_length=128, regex=re.compile(r'.*(\-\-save \$new_filename).*(\$filename).*$'), label='COPASI arguments', help_text='Arguments to add when running COPASI. Must contain <b>$filename</b> and <b>--save $new_filename</b> as arguments.', widget=forms.TextInput(attrs={'size':'40'}), required=True, initial='--nologo --home . --save $new_filename $filename') #TODO: update this regex so that it won't match certain characters, e.g. ';','|', '&' etc (though perhaps this isn't necessary)

class TaskPlugin(BaseTask):

    subtasks = 3

    def __init__(self, task):

        self.repeats = task.get_custom_field('repeats')
        self.data_files = task.get_custom_field('data_files')
        if self.data_files is None:
           self.data_files = []
        self.raw_mode_args = task.get_custom_field('raw_mode_args')



        super(TaskPlugin, self).__init__(task)
        log.debug("+++++++++++ Running BasiCO implementation.")
        log.debug("+++++++++++ self.task.directory: %s" %self.task.directory)
        log.debug("+++++++++++ self.task.original_model: %s" %self.task.original_model)
        self.copasi_model = RWCopasiModel_BasiCO(os.path.join(self.task.directory, self.task.original_model))



    def validate(self):
        #TODO:Abstract this to a new COPASI class in this plugin package
        return self.copasi_model.is_valid('RW')

    def initialize_subtasks(self):
        #Create new subtask objects, and save them
        #The main module
        self.create_new_subtask('main')
        #And a subtask to process any results
        self.create_new_subtask('process', local=True)

        self.task.result_view = False
        self.task.result_download = False
        self.task.save()

    def prepare_subtask(self, index):
        """Prepare the indexed subtask"""

        if index == 1:
            return self.process_main_subtask()

        elif index == 2:
            return self.process_results_subtask()
        else:
            raise Exception('No subtasks remaining')




    def process_main_subtask(self):

        subtask = self.get_subtask(1)

        #If no load balancing step required:
        model_files, output_files = self.copasi_model.prepare_rw_jobs(self.repeats)

        self.task.set_custom_field('output_files', output_files)
        model_count = len(model_files)
        self.task.set_custom_field('model_count', model_count)

        self.task.save()

        condor_pool = self.task.condor_pool

        condor_job_file = self.copasi_model.prepare_rw_condor_job(condor_pool.pool_type, condor_pool.address, len(model_files), self.raw_mode_args, self.data_files, output_files, rank='0')

        log.debug('Prepared copasi files %s'%model_files)
        log.debug('Prepared condor job %s' %condor_job_file)



        subtask.spec_file = condor_job_file
        subtask.status = 'ready'
        subtask.set_custom_field('job_output', '') # Job output is potentially >1 file. Currently can't check for this, so leave blank
        subtask.save()

        return subtask


    def process_results_subtask(self):
        subtask=self.get_subtask(2)
        assert isinstance(subtask, Subtask)

        #subtask.start_time = now()
        subtask.start_time = timezone.localtime()
        temp_start_time = subtask.start_time
        slog.debug("temp_start_time: {}".format(temp_start_time))

        #Go through and collate the results
        #This is reasonably computationally simple, so we run locally

        directory = self.task.directory

        output_files = self.task.get_custom_field('output_files')

        model_count = self.task.get_custom_field('model_count')

        collated_output_files = []
        #Collate the output files back into their original name
        for output_filename in output_files:
            try:
                output_file = open(os.path.join(directory, output_filename), 'w')
                log.debug(" ---------- output_file")
                log.debug(output_file)

                for partial_output in ['%d_%s' % (i, output_filename) for i in range(model_count)]:
                    partial_output_file = open(os.path.join(directory, partial_output), 'r')
                    for line in partial_output_file:
                        output_file.write(line)
                    partial_output_file.close()
                output_file.close()
                collated_output_files.append(output_filename)
            except Exception as e:
                raise e
                pass

        self.task.set_custom_field('collated_output_files', collated_output_files)
        if len(collated_output_files) > 0:
            self.task.result_view=True
        self.task.save()

        # time.sleep(30)  #adding 30 seconds delay to observe timings of local task

        subtask.status = 'finished'
        subtask.finish_time = timezone.localtime()
        temp_finish_time = subtask.finish_time

        slog.debug("temp_finish_time: {}".format(temp_finish_time))

        time_delta = temp_finish_time - temp_start_time

        slog.debug("Time Delta RAW MODE: {}".format(time_delta))

        # slog.debug("Calling set_run_time method from RAWMODE plugin with time_delta value")
        subtask.set_run_time(time_delta)

        subtask.save()
        subtask.task.save()

        return subtask

    #===========================================================================
    # Results download code. No results view page for this task
    #===========================================================================

    def get_results_view_template_name(self, request):
        """Return a string with the HTML code to be used in the task results view page
        """
        #Get the name of the page we're displaying. If not specified, assume main
        page_name = request.GET.get('name', 'main')

        if page_name == 'main':
            return self.get_template_name('results_view')


    def get_results_view_data(self, request):
        #Get the name of the page we're displaying. If not specified, assume main
        page_name = request.GET.get('name', 'main')
        if page_name == 'main':
            collated_output_files = self.task.get_custom_field('collated_output_files')
            #output = {'output_files': collated_output_files}
            #added by HB -----
            repeats = self.repeats
            output = {'output_files': collated_output_files,
                      'repeats': repeats,
            }
            #-----------
            return output

    def get_results_download_data(self, request):
        filename = request.GET.get('name')


        if not filename in self.task.get_custom_field('collated_output_files'):
            raise Exception('Output file not recognized')
            request.session['errors'] = [('Cannot Return Output', 'There was an internal error processing the results file')]
            return HttpResponseRedirect(reverse_lazy('task_details', kwargs={'task_id':self.task.id}))



        full_filename = os.path.join(self.task.directory, filename)
        if not os.path.isfile(full_filename):
            request.session['errors'] = [('Cannot Return Output', 'There was an internal error processing the results file')]
            return HttpResponseRedirect(reverse_lazy('task_details', kwargs={'task_id':self.task.id}))
        result_file = open(full_filename, 'r')
        response = HttpResponse(result_file, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename=%s' % (filename.replace(' ', '_'))
        response['Content-Length'] = os.path.getsize(full_filename)

        return response
