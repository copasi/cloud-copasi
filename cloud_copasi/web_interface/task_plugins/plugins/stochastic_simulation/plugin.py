# -------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# -------------------------------------------------------------------------------

from cloud_copasi.web_interface.task_plugins.base import BaseTask, BaseTaskForm
from cloud_copasi.web_interface.models import Task, CondorJob, CondorPool
from cloud_copasi.web_interface.models import Subtask
from django.forms import Form
from django import forms
from cloud_copasi import settings
from cloud_copasi.copasi.model import CopasiModel, CopasiModel_BasiCO
from cloud_copasi.web_interface.task_plugins.plugins.stochastic_simulation.copasi_model import SSCopasiModel, SSCopasiModel_BasiCO  # Use the task-specific copasi model in this directory
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

os.environ['HOME'] = settings.STORAGE_DIR  # This needs to be set to a writable directory
import matplotlib

matplotlib.use(
    'Agg')  # Use this so matplotlib can be used on a headless server. Otherwise requires DISPLAY env variable to be set.
import matplotlib.pyplot as plt
import io #added by HB
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

internal_type = ('stochastic_simulation', 'Stochastic simulation')


class TaskForm(BaseTaskForm):
    # Any extra fields for the task submission form
    skip_load_balancing_step = forms.BooleanField(required=False,
                                                  help_text='Select this to skip the automatic load balancing step, and make the run time of each parallel job as short as possible. <span class="bold">Use with caution! This has the potential to overload the Condor system with huge numbers of parallel jobs.</span> Not applicable for some job types - see documentation for further details.')
    repeats = forms.IntegerField(required=True, min_value=1, help_text='The number of repeats to perform.')


class TaskPlugin(BaseTask):
    subtasks = 2

    def __init__(self, task):
        self.use_load_balancing = not task.get_custom_field('skip_load_balancing_step')

        if self.use_load_balancing:
            self.subtasks = 3
        else:
            self.subtasks = 2
            task.set_custom_field('repeats_per_job', 1)

        super(TaskPlugin, self).__init__(task)
        #check.debug('~~~~~~~~~~~~ Running LXML Implementation')
        #self.copasi_model = SSCopasiModel(os.path.join(self.task.directory, self.task.original_model))
        check.debug("+++++++++++ Running BasiCO implementation.")
        self.copasi_model = SSCopasiModel_BasiCO(os.path.join(self.task.directory, self.task.original_model))

        self.repeats = self.task.get_custom_field('repeats')
        repeats = self.repeats

    def validate(self):
        # TODO:Abstract this to a new COPASI class in this plugin package
        return self.copasi_model.is_valid('SS')

    def initialize_subtasks(self):
        # Create new subtask objects, and save them
        if self.use_load_balancing:
            # Create the load balancing module
            self.create_new_subtask('lb')

        # The main module
        self.create_new_subtask('main')
        # And a subtask to process any results
        self.create_new_subtask('process')

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
            assert self.use_load_balancing
            return self.process_results_subtask()
        else:
            raise Exception('No subtasks remaining')

    def process_lb_subtask(self):
        # Prepare the necessary files to run the load balancing task on condor

        filenames = self.copasi_model.prepare_ss_load_balancing()
        # Construct the model files for this task
        timeout = str(settings.IDEAL_JOB_TIME * 60)
        if self.task.get_custom_field('rank'):
            rank = str(self.task.get_custom_field('rank'))
        else:
            rank = ''

        # model_filename = self.task.original_model

        copasi_binary_dir, copasi_binary = os.path.split(settings.COPASI_LOCAL_BINARY)

        # write the load balancing script
        load_balacing_script_template = Template(load_balancing.load_balancing_string)
        load_balancing_script_string = load_balacing_script_template.substitute(timeout=timeout,
                                                                                copasi_binary='./' + copasi_binary,
                                                                                copasi_file_1=('load_balancing_1.cps'),
                                                                                copasi_file_10=('load_balancing_10.cps'),
                                                                                copasi_file_100=('load_balancing_100.cps'),
                                                                                copasi_file_1000=('load_balancing_1000.cps'),
                                                                                )
        load_balancing_script_filename = 'load_balance.sh'
        load_balancing_file = open(os.path.join(self.task.directory, load_balancing_script_filename), 'w')
        load_balancing_file.write(load_balancing_script_string)
        load_balancing_file.close()

        copasi_files_string = ''
        for repeat in [1, 10, 100, 1000]:
            copasi_files_string += 'load_balancing_%d.cps, ' % repeat
        copasi_files_string = copasi_files_string.rstrip(', ')  # Remove final comma

        load_balancing_condor_template = Template(
            condor_spec.condor_string_header + condor_spec.load_balancing_spec_string)
        load_balancing_condor_string = load_balancing_condor_template.substitute(
            pool_type=self.task.condor_pool.pool_type,
            pool_address=self.task.condor_pool.address,
            script=load_balancing_script_filename,
            copasi_binary=settings.COPASI_LOCAL_BINARY,
            arguments=str(timeout),
            rank=rank,
            copasi_files=copasi_files_string,
            )
        # write to the condor file
        condor_file = open(os.path.join(self.task.directory, 'load_balancing.job'), 'w')
        condor_file.write(load_balancing_condor_string)
        condor_file.close()

        subtask = self.get_subtask(1)

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

        # Get the correct subtask
        if self.use_load_balancing:
            subtask = self.get_subtask(2)

            lb_job = CondorJob.objects.get(subtask=self.get_subtask(1))
            # Read the load_balancing.out file

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

                # Work out the number of repeats per job. If this is more than the original number of repeats specified, then just use the original number
                repeats_per_job = min(int(round(settings.IDEAL_JOB_TIME * 60 / time_per_run)), self.repeats)

                if repeats_per_job < 1:
                    repeats_per_job = 1



        else:
            subtask = self.get_subtask(1)
            repeats_per_job = 1

        # If no load balancing step required:
        model_files = self.copasi_model.prepare_ss_task(self.repeats, repeats_per_job, subtask.index)

        condor_pool = self.task.condor_pool

        condor_job_file = self.copasi_model.prepare_ss_condor_job(condor_pool.pool_type, condor_pool.address,
                                                                  len(model_files), subtask.index, rank='')

        check.debug('Prepared copasi files %s' % model_files)
        check.debug('Prepared condor job %s' % condor_job_file)

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

        # Go through and collate the results
        # This is a computationally expensive task, so we will run on condor

        directory = self.task.directory

        main_jobs = CondorJob.objects.filter(subtask=main_subtask)

        # Get the path of the results_process script
        path = os.path.abspath(__file__)
        dir_path = os.path.dirname(path)
        script = os.path.join(dir_path, 'results_process.py')

        condor_job = self.copasi_model.prepare_ss_process_job(subtask.task.condor_pool.pool_type,
                                                              subtask.task.condor_pool.address, main_jobs, script)

        subtask.set_custom_field('std_output_file', 'results.out')
        subtask.set_custom_field('std_err_file', 'results.err')
        subtask.set_custom_field('log_file', 'results.log')
        subtask.set_custom_field('job_output', 'results.txt')
        subtask.set_custom_field('copasi_model', '')
        subtask.spec_file = condor_job
        log.debug('Setting subtask as ready to submit with spec file %s' % subtask.spec_file)
        subtask.status = 'ready'
        subtask.save()

        return subtask

    # ===========================================================================
    # Results view code, including a form to update the plot
    # ===========================================================================

    def get_results_view_template_name(self, request):
        """Return a string with the HTML code to be used in the task results view page
        """
        # Get the name of the page we're displaying. If not specified, assume main
        page_name = request.GET.get('name', 'main')

        if page_name == 'main':
            return self.get_template_name('stochastic_plot')

        else:
            return ''

    def get_results_view_data(self, request):
        # Get the name of the page we're displaying. If not specified, assume main
        page_name = request.GET.get('name', 'main')
        if page_name == 'main':
            model = self.copasi_model
            try:
                variable_choices = model.get_variables(pretty=True)
            except:
                raise

            # If the variables GET field hasn't been set, preset it to all variables

            try:
                assert request.GET.get('custom') == 'true'
                form = PlotUpdateForm(request.GET, variable_choices=variable_choices)
            except:
                form = PlotUpdateForm(variable_choices=variable_choices,
                                      initial={'variables': range(len(variable_choices))})

            if form.is_valid():
                variables = map(int, form.cleaned_data['variables'])
                log = form.cleaned_data['logarithmic']
                stdev = form.cleaned_data['stdev']
                legend = form.cleaned_data['legend']
                grid = form.cleaned_data['grid']
                fontsize = form.cleaned_data['fontsize']
            else:
                variables = range(len(variable_choices))
                log = False
                stdev = True
                legend = True
                grid = True
                fontsize = '12'

            # construct the string to load the image file
            img_string = '?variables=' + str(variables).strip('[').rstrip(']').replace(' ', '')
            img_string += '&name=plot'
            if log:
                img_string += '&log=true'
            if stdev:
                img_string += '&stdev=true'
            if legend:
                img_string += '&legend=true'
            if grid:
                img_string += '&grid=true'
            if fontsize:
                img_string += '&fontsize=' + str(fontsize)

            output = {'form': form, 'img_string': img_string}

            return output

    def get_results_download_data(self, request):
        page_name = request.GET.get('name', 'main')

        if page_name == 'main':
            # Return the file results.txt
            filename = os.path.join(self.task.directory, 'results.txt')
            if not os.path.isfile(filename):
                request.session['errors'] = [
                    ('Cannot Return Output', 'There was an internal error processing the results file')]
                return HttpResponseRedirect(reverse_lazy('task_details', kwargs={'task_id': self.task.id}))
            result_file = open(filename, 'r')
            response = HttpResponse(result_file, content_type='text/tab-separated-values')
            response['Content-Disposition'] = 'attachment; filename=%s_results.txt' % (self.task.name.replace(' ', '_'))
            response['Content-Length'] = os.path.getsize(filename)

            return response

        elif page_name == 'plot':
            return self.get_stochastic_plot(request)

    def get_stochastic_plot(self, request):
        """Return the plot image for the results from a stochastic simulation"""
        import numpy as np
        task = self.task
        model = self.copasi_model
        try:
            assert task.status == 'finished'
            results = np.loadtxt(os.path.join(task.directory, 'results.txt'), skiprows=1, delimiter='\t', unpack=True)
            variable_list = model.get_variables(pretty=True)

        except Exception as e:
            log.exception(e)
            raise e
        try:

            # Look at the GET data to see what chart options have been set:
            #get_variables = request.GET.get('variables')
            #above line is modified by HB as follows
            get_variables = request.GET.get('variables','')
            log = request.GET.get('log', 'false')
            stdev = request.GET.get('stdev', 'false')
            legend = request.GET.get('legend', 'false')
            grid = request.GET.get('grid', 'false')
            fontsize = int(request.GET.get('fontsize', '12'))

            # Check to see if we should return as an attachment in .png or .svg or .pdf
            download_png = 'download_png' in request.POST
            download_svg = 'download_svg' in request.POST
            download_pdf = 'download_pdf' in request.POST

            try:
                variables = map(int, get_variables.split(','))
                assert max(variables) < ((len(results) - 1) / 2)
            except:
                variables = range(int((len(results) - 1) / 2))

            matplotlib.rc('font', size=fontsize)
            fig = plt.figure()
            # plt.title(job.name + ' (' + str(job.runs) + ' repeats)', fontsize=12, fontweight='bold')
            plt.xlabel('Time')

            color_list = ['red', 'blue', 'green', 'cyan', 'magenta', 'yellow', 'black']
            #        import random
            #        random.shuffle(color_list)
            # Regex for extracting the variable name from the results file.
            label_str = r'(?P<name>.+)\[.+\] (mean|stdev)$'
            label_re = re.compile(label_str)

            j = 0  # used to keep cycle through colors in order
            for i in variables:
                # Go through each result and plot mean and stdev against time
                label = variable_list[i]

                # Plot the means
                plt.plot(results[0], results[2 * i + 1], lw=2, label=label, color=color_list[j % 7])

                if stdev == 'true':
                    # Calculate stdev upper and lower bounds (mean +/- stdev) and shade the stdevs if requested
                    upper_bound = results[2 * i + 1] + results[2 * i + 2]
                    lower_bound = results[2 * i + 1] - results[2 * i + 2]
                    plt.fill_between(results[0], upper_bound, lower_bound, alpha=0.2, color=color_list[j % 7])
                j += 1
            # Set a logarithmic scale if requested
            if log != 'false':
                plt.yscale('log')
            if legend != 'false':
                plt.legend(loc=0, prop={'size': fontsize})
            if grid != 'false':
                plt.grid(True)

            name = self.task.name.replace(' ', '_')
            if download_png:
                #response = HttpResponse(mimetype='image/png', content_type='image/png')
                #above line is modified by HB as follows
                response = HttpResponse(content_type='image/png')
                fig.savefig(response, format='png', transparent=False, dpi=120)
                response['Content-Disposition'] = 'attachment; filename=%s.png' % name
            elif download_svg:
                #response = HttpResponse(mimetype='image/svg', content_type='image/svg')
                #fig.savefig(response, format='svg', transparent=False, dpi=120)
                #response['Content-Disposition'] = 'attachment; filename=%s.svg' % name

                #above lines are modified by HB as follows
                buf = io.BytesIO()
                fig.savefig(buf, format='svg', transparent=False, dpi=120)
                response = HttpResponse(buf.getvalue(), content_type='image/svg')
                response['Content-Disposition'] = 'attachment; filename=%s.svg' % name


            elif download_pdf:
                #response = HttpResponse(mimetype='application/pdf', content_type='application/pdf')
                #fig.savefig(response, format='pdf', transparent=False, dpi=120)
                #response['Content-Disposition'] = 'attachment; filename=%s.pdf' % name

                #above lines are modified by HB as follows
                buf = io.BytesIO()
                fig.savefig(buf, format='pdf', transparent=False, dpi=120)
                response = HttpResponse(buf.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=%s.pdf' % name

            else:
                #response = HttpResponse(mimetype='image/png', content_type='image/png')
                #above line is modified by HB as follows
                response = HttpResponse(content_type='image/png')
                fig.savefig(response, format='png', transparent=False, dpi=120)
            return response

        except Exception as e:
            check.exception(e)
            raise e


# form to update the stochastic simulation plots
class PlotUpdateForm(forms.Form):
    """Form containing controls to update plots"""

    def __init__(self, *args, **kwargs):
        variables = kwargs.pop('variable_choices', None)
        variable_choices = []
        for i in range(len(variables)):
            variable_choices.append((i, variables[i]))

        super(PlotUpdateForm, self).__init__(*args, **kwargs)
        self.fields['variables'].choices = variable_choices

    legend = forms.BooleanField(label='Show figure legend', required=False, initial=True)
    stdev = forms.BooleanField(label='Show standard deviations', required=False, initial=True)
    grid = forms.BooleanField(label='Show grid', required=False, initial=True)
    logarithmic = forms.BooleanField(label='Logarithmic scale', required=False)
    variables = forms.MultipleChoiceField(choices=(), widget=forms.CheckboxSelectMultiple(), required=True)
    fontsize = forms.IntegerField(label='Font size', required=False, initial='12')
    # Add the name=plot parameter to the GET data so we get the right page back
