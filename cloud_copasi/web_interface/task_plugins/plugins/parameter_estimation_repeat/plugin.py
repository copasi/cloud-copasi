#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from cloud_copasi.web_interface.task_plugins.base import BaseTask, BaseTaskForm
from cloud_copasi.web_interface.models import Task, CondorJob, CondorPool
from cloud_copasi.web_interface.models import Subtask
from django.forms import Form
from django import forms
from cloud_copasi import settings
from cloud_copasi.copasi.model import CopasiModel_BasiCO
from cloud_copasi.web_interface.task_plugins.plugins.parameter_estimation_repeat.copasi_model import PRCopasiModel_BasiCO # Use the task-specific copasi model in this directory
import os, math
import logging
from django.http.response import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from cloud_copasi.condor import condor_spec
from string import Template
from cloud_copasi.web_interface.task_plugins import load_balancing
import re
import datetime
#from django.utils.timezone import now
from django.utils import timezone #added by HB

log = logging.getLogger(__name__)

os.environ['HOME'] = settings.STORAGE_DIR #This needs to be set to a writable directory
import matplotlib
matplotlib.use('Agg') #Use this so matplotlib can be used on a headless server. Otherwise requires DISPLAY env variable to be set.
import matplotlib.pyplot as plt
from matplotlib.pyplot import annotate

########### following lines are set by HB for debugging
logging.basicConfig(
        filename='/home/cloudcopasi/log/debug.log',
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%m/%d/%y %I:%M:%S %p',
        level=logging.DEBUG
    )
check = logging.getLogger(__name__)
######################################################

internal_type = ('parameter_estimation_repeat', 'Parameter estimation repeat')

class TaskForm(BaseTaskForm):
    #Any extra fields for the task submission form
    parameter_estimation_data = forms.FileField(required=True, help_text='Select either a single data file, or if more than one data file is required, upload a .zip file containing multiple data files.')
    repeats = forms.IntegerField(required=True, min_value=1, help_text='The number of repeats to perform.')
    custom_report = forms.BooleanField(required=False, label='Use a custom report', help_text='Select this to use a custom report instead of the automatically generated one. If you select this, Condor-COPASI may not be able to process the output data, and the job will fail. However, you will still be able download the unprocessed results for manual processing. For output processing to work, you must create a report with custom fields added before the fields that would otherwise be automatically generated (Best Parameters, Best Value, CPU Time and Function Evaluations).')
    skip_load_balancing_step = forms.BooleanField(required=False, help_text='Select this to skip the automatic load balancing step, and make the run time of each parallel job as short as possible. <span class="bold">Use with caution! This has the potential to overload the Condor system with huge numbers of parallel jobs.</span> Not applicable for some job types - see documentation for further details.')

class TaskPlugin(BaseTask):

    subtasks = 2

    def __init__(self, task):
        self.use_load_balancing = not task.get_custom_field('skip_load_balancing_step')
        self.data_files = task.get_custom_field('data_files')
        if self.use_load_balancing:
            self.subtasks = 4
        else:
            self.subtasks = 3
            task.set_custom_field('repeats_per_job', 1)

        super(TaskPlugin, self).__init__(task)

        check.debug("+++++++++++ Running BasiCO implementation.")
        self.copasi_model = PRCopasiModel_BasiCO(os.path.join(self.task.directory, self.task.original_model))
        self.repeats = self.task.get_custom_field('repeats')
        self.custom_report = self.task.get_custom_field('custom_report')
        repeats = self.repeats

    def validate(self):
        #TODO:Abstract this to a new COPASI class in this plugin package
        return self.copasi_model.is_valid('PR')

    def initialize_subtasks(self):
        #Create new subtask objects, and save them
        if self.use_load_balancing:
            #Create the load balancing module
            self.create_new_subtask('lb')

        #The main module
        self.create_new_subtask('main')
        #And a subtask to process any results
        self.create_new_subtask('process', local=True)

        self.create_new_subtask('file')

    def prepare_subtask(self, index):
        """Prepare the indexed subtask"""

        if index == 1:
            if self.use_load_balancing:
                return self.process_lb_subtask()
            else:
                return self.process_main_subtask()

        elif index == 2:
            if self.use_load_balancing:
                return self.process_main_subtask()
            else:
                return self.process_results_subtask()
        elif index == 3:
            if self.use_load_balancing:
                return self.process_results_subtask()
            else:
                return self.create_optimal_file()
        elif index == 4:
            if not self.use_load_balancing:
                raise Exception('No subtasks remaining')
            else:
                return self.create_optimal_file()

    def process_lb_subtask(self):
        #Prepare the necessary files to run the load balancing task on condor

        filenames = self.copasi_model.prepare_pr_load_balancing()
        #Construct the model files for this task
        timeout = str(settings.IDEAL_JOB_TIME * 60)
        if self.task.get_custom_field('rank'):
            rank = str(self.task.get_custom_field('rank'))
        else:
            rank = ''

        #model_filename = self.task.original_model

        copasi_binary_dir, copasi_binary = os.path.split(settings.COPASI_LOCAL_BINARY)

        #write the load balancing script
        load_balacing_script_template = Template(load_balancing.load_balancing_string)
        load_balancing_script_string = load_balacing_script_template.substitute(timeout=timeout,
                                                                 copasi_binary='./' + copasi_binary,
                                                                 copasi_file_1 = ('load_balancing_1.cps'),
                                                                 copasi_file_10 = ('load_balancing_10.cps'),
                                                                 copasi_file_100 = ('load_balancing_100.cps'),
                                                                 copasi_file_1000 = ('load_balancing_1000.cps'),
                                                                 )
        load_balancing_script_filename = 'load_balance.sh'
        load_balancing_file = open(os.path.join(self.task.directory, load_balancing_script_filename), 'w')
        load_balancing_file.write(load_balancing_script_string)
        load_balancing_file.close()

        copasi_files_string = ''
        for repeat in [1, 10, 100, 1000]:
            copasi_files_string += 'load_balancing_%d.cps, ' % repeat
        for data_file in self.data_files:
            copasi_files_string += data_file + ', '
        copasi_files_string = copasi_files_string.rstrip(', ') #Remove final comma

        load_balancing_condor_template = Template(condor_spec.condor_string_header + condor_spec.load_balancing_spec_string)
        load_balancing_condor_string = load_balancing_condor_template.substitute(pool_type=self.task.condor_pool.pool_type,
                                                                   pool_address = self.task.condor_pool.address,
                                                                   script = load_balancing_script_filename,
                                                                   copasi_binary=settings.COPASI_LOCAL_BINARY,
                                                                   arguments = str(timeout),
                                                                   rank=rank,
                                                                   copasi_files=copasi_files_string,
                                                                   )
        #write to the condor file
        condor_file = open(os.path.join(self.task.directory, 'load_balancing.job'), 'w')
        condor_file.write(load_balancing_condor_string)
        condor_file.close()

        subtask=self.get_subtask(1)

        subtask.spec_file = 'load_balancing.job'
        subtask.status = 'waiting'

        subtask.set_custom_field('std_output_file', 'load_balancing.out')
        subtask.set_custom_field('std_err_file', 'load_balancing.err')
        subtask.set_custom_field('log_file', 'load_balancing.log')
        subtask.set_custom_field('job_output', '')
        subtask.set_custom_field('copasi_model', 'load_balancing.cps')


        subtask.save()

        return subtask

    def process_main_subtask(self):


        #Get the correct subtask
        if self.use_load_balancing:
            subtask = self.get_subtask(2)

            lb_job = CondorJob.objects.get(subtask=self.get_subtask(1))
            #Read the load_balancing.out file

            output = open(os.path.join(subtask.task.directory, lb_job.std_output_file), 'r')


            for line in output.readlines():
                line = line.rstrip('\n')
                if line != '':
                    repeats_str, time_str = line.split(' ')

                try:
                    lb_repeats = int(repeats_str)
                    time = float(time_str)
                except Exception as e:
                    log.exception(e)
                    lb_repeats = 1
                    time = settings.IDEAL_JOB_TIME

                time_per_run = time / lb_repeats

                #Work out the number of repeats per job. If this is more than the original number of repeats specified, then just use the original number
                repeats_per_job = min(int(round(settings.IDEAL_JOB_TIME * 60 / time_per_run)), self.repeats)

                if repeats_per_job < 1:
                    repeats_per_job = 1



        else:
            subtask = self.get_subtask(1)
            repeats_per_job = 1




        #If no load balancing step required:
        model_files = self.copasi_model.prepare_pr_jobs(self.repeats, repeats_per_job, subtask.index, self.custom_report)

        condor_pool = self.task.condor_pool

        condor_job_file = self.copasi_model.prepare_pr_condor_job(condor_pool.pool_type,
                                                                  condor_pool.address,
                                                                  len(model_files),
                                                                  subtask.index,
                                                                  self.data_files,
                                                                  rank='')

        check.debug('Prepared copasi files %s'%model_files)
        check.debug('Prepared condor job %s' %condor_job_file)

        model_count = len(model_files)
        self.task.set_custom_field('model_count', model_count)


        subtask.spec_file = condor_job_file
        subtask.status = 'ready'
        subtask.save()

        return subtask


    def process_results_subtask(self):
        if self.use_load_balancing:
            main_subtask = self.get_subtask(2)
            subtask = self.get_subtask(3)
        else:
            main_subtask = self.get_subtask(1)
            subtask = self.get_subtask(2)

        assert isinstance(subtask, Subtask)

        #subtask.start_time = now()
        #above line is modified by HB as follows
        subtask.start_time = timezone.localtime()

        temp_start_time = subtask.start_time

        #Go through and collate the results
        #This is reasonably computationally simple, so we run locally

        directory = self.task.directory

        main_jobs = CondorJob.objects.filter(subtask=main_subtask)

        results_files = [job.job_output for job in main_jobs]

        success = self.copasi_model.process_pr_results(results_files, self.custom_report)


        if not success:
            self.task.results_view = False
            self.task.results_download = False

            #Delete the final subtask
            if self.use_load_balancing:
                final_subtask_index = 4
            else:
                final_subtask_index = 3
            final_subtask = Subtask.objects.filter(task=self.task).get(index=final_subtask_index)
            check.debug('deleting model creation subtask since no results could be identified in output')
            final_subtask.delete()
        else:
            self.task.results_view = True
            self.task.results_download = True

        self.task.save()
        subtask.status = 'finished'

        subtask.finish_time = timezone.localtime()

        temp_finish_time = subtask.finish_time

        #added by HB
        time_delta = temp_finish_time - temp_start_time

        check.debug("Time Delta: ")
        check.debug(time_delta)
        subtask.set_run_time(time_delta)

        subtask.save()


        return subtask


    def create_optimal_file(self):
        """Create a copasi file containing the best values
        """

        if self.use_load_balancing:
            subtask = self.get_subtask(4)
        else:
            subtask = self.get_subtask(3)

        optimal_model = self.copasi_model.create_pr_best_value_model(subtask.index, custom_report=self.custom_report)
        condor_pool = self.task.condor_pool

        optimal_condor_job_file = self.copasi_model.prepare_pr_optimal_model_condor_job(condor_pool.pool_type,
                                                                  condor_pool.address,
                                                                  1,
                                                                  subtask.index,
                                                                  self.data_files,
                                                                  rank='')
        subtask.status = 'ready'
        subtask.spec_file = optimal_condor_job_file
        subtask.set_custom_field('job_output', '')
        subtask.save()

        return subtask

    #===========================================================================
    # Results view code, including a form to update the plot
    #===========================================================================


    def get_results_view_template_name(self, request):
        """Return a string with the HTML code to be used in the task results view page
        """
        #Get the name of the page we're displaying. If not specified, assume main
        page_name = request.GET.get('name', 'main')

        if page_name == 'main':
            return self.get_template_name('results_view')

        else: return ''


    def get_results_view_data(self, request):
        #Get the name of the page we're displaying. If not specified, assume main
        page_name = request.GET.get('name', 'main')
        if page_name == 'main':
            model = self.copasi_model
            results = model.get_or_best_value()

            best_value = results[0][1]

            best_params = results[1:]

            output = {'best_value' : best_value,
                      'best_params' : best_params,
                      }

            return output

    def get_results_download_data(self, request):
        page_name = request.GET.get('name', 'main')

        if page_name == 'main':
            #Return the file results.txt
            filename = os.path.join(self.task.directory, 'results.txt')
            if not os.path.isfile(filename):
                request.session['errors'] = [('Cannot Return Output', 'There was an internal error processing the results file')]
                return HttpResponseRedirect(reverse_lazy('task_details', kwargs={'task_id':self.task.id}))
            result_file = open(filename, 'r')
            response = HttpResponse(result_file, content_type='text/tab-separated-values')
            response['Content-Disposition'] = 'attachment; filename=%s_results.txt' % (self.task.name.replace(' ', '_'))
            response['Content-Length'] = os.path.getsize(filename)

            return response

        elif page_name == 'raw_results':
            filename = os.path.join(self.task.directory, 'raw_results.txt')
            if not os.path.isfile(filename):
                request.session['errors'] = [('Cannot Return Output', 'There was an internal error processing the results file')]
                return HttpResponseRedirect(reverse_lazy('task_details', kwargs={'task_id':self.task.id}))
            result_file = open(filename, 'r')
            response = HttpResponse(result_file, content_type='text/tab-separated-values')
            response['Content-Disposition'] = 'attachment; filename=%s_raw_results.txt' % (self.task.name.replace(' ', '_'))
            response['Content-Length'] = os.path.getsize(filename)

            return response

        elif page_name == 'optimal_model':

            subtask_count = Subtask.objects.filter(task=self.task).count()

            optimal_filename = 'run_auto_copasi_%d.0.cps' % subtask_count
            filename = os.path.join(self.task.directory, optimal_filename)
            if not os.path.isfile(filename):
                request.session['errors'] = [('Cannot Return Output', 'There was an internal error processing the results file')]
                return HttpResponseRedirect(reverse_lazy('task_details', kwargs={'task_id':self.task.id}))
            result_file = open(filename, 'r', encoding='utf8')
            #added by HB
            #result_file = result_file.decode('utf-8')
            #response = HttpResponse(result_file, content_type='application/xml', charset='utf-8')
            response = HttpResponse(result_file, content_type='application/xml', charset='utf-8')
            response['Content-Disposition'] = 'attachment; filename=%s_optimal_model.cps' % (self.task.name.replace(' ', '_'))
            response['Content-Length'] = os.path.getsize(filename)

            return response
