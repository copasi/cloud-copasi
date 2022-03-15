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
from cloud_copasi.copasi.model import CopasiModel_BasiCO
import os, math
import logging
from django.http.response import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
import datetime
#from django.utils.timezone import now
from django.utils import timezone #added by HB

log = logging.getLogger(__name__)

os.environ['HOME'] = settings.STORAGE_DIR #This needs to be set to a writable directory
import matplotlib
matplotlib.use('Agg') #Use this so matplotlib can be used on a headless server. Otherwise requires DISPLAY env variable to be set.
import matplotlib.pyplot as plt
import io   #added by HB
from matplotlib.pyplot import annotate

internal_type = ('sensitivity_optimization', 'Sensitivity optimization')

class TaskForm(BaseTaskForm):
    #Any extra fields for the task submission form
    pass


class TaskPlugin(BaseTask):

    subtasks = 2

    def __init__(self, *args, **kwargs):
        super(TaskPlugin, self).__init__(*args, **kwargs)
        log.debug("+++++++++++ Running BasiCO implementation.")
        self.copasi_model = CopasiModel_BasiCO(os.path.join(self.task.directory, self.task.original_model))


    def validate(self):
        #TODO:Abstract this to a new COPASI class in this plugin package
        return self.copasi_model.is_valid('SO')

    def initialize_subtasks(self):
        #Create new subtask objects, and save them

        #Create the main subtask
        self.create_new_subtask('main')
        #And a subtask to process any results
        self.create_new_subtask('process', local=True)

    def prepare_subtask(self, index):
        """Prepare the indexed subtask"""

        if index == 1:
            return self.process_first_subtask()
        elif index == 2:
            return self.process_second_subtask()
        else:
            raise Exception('No subtasks remaining')


    def process_first_subtask(self):
        #Get the first subtask
        subtask = self.get_subtask(1)

        #Construct the model files for this task


        model_path, model_filename = os.path.split(self.task.original_model)

        #If no load balancing step required:
        log.debug("initializing prepare_so_task()")
        model_files = self.copasi_model.prepare_so_task()
        log.debug("returned back from prepare_so_task()")

        condor_pool = self.task.condor_pool

        condor_job_file = self.copasi_model.prepare_so_condor_job(condor_pool.pool_type, condor_pool.address, subtask_index=1, rank='')

        log.debug('Prepared copasi files %s'%model_files)
        log.debug('Prepared condor job %s' %condor_job_file)

        model_count = len(model_files)
        self.task.set_custom_field('model_count', model_count)


        subtask.spec_file = condor_job_file
        subtask.status = 'ready'
        subtask.save()

        return subtask


    def process_second_subtask(self):
        subtask=self.get_subtask(2)
        assert isinstance(subtask, Subtask)

        log.debug("+++++++++++ process_second_subtask() executed")
        #subtask.start_time = now()
        #above line is modified by HB as follows
        subtask.start_time = timezone.localtime()
        temp_start_time = subtask.start_time

        #Go through and collate the results
        #This is a computationally simple task, so we will run locally, not remotely

        directory = self.task.directory

        original_subtask = self.get_subtask(1)

        output_filename = 'output_1.%d.txt'

        results = self.copasi_model.get_so_results(save=True)

        subtask.task.set_custom_field('results_file', 'results.txt')

        log.debug('Setting subtask as finished')
        subtask.status = 'finished'
        subtask.finish_time = timezone.localtime()
        temp_finish_time = subtask.finish_time

        time_delta = temp_finish_time - temp_start_time
        log.debug("Time Delta: ")
        log.debug(time_delta)

        subtask.save()

        return subtask

    def get_results_view_template_name(self, request):
        """Return a string with the HTML code to be used in the task results view page
        """
        #Get the name of the page we're displaying. If not specified, assume main
        page_name = request.GET.get('name', 'main')


        if page_name == 'main':
            return self.get_template_name('results_view')
        elif page_name == 'plot':
            return self.get_template_name('progress_plot')
        else: return ''


    def get_results_view_data(self, request):
        #Get the name of the page we're displaying. If not specified, assume main
        page_name = request.GET.get('name', 'main')

        if page_name == 'main':
            results = self.copasi_model.get_so_results(save=False)
            output = {'results': results}
            output['sensitivity_object'] = self.copasi_model.get_sensitivities_object()

            return output
        elif page_name == 'plot':
            output = {}

            results = self.copasi_model.get_so_results()
            variable_choices=[]
            for result in results:
                variable_choices.append(result['name'] + '_max')
                variable_choices.append(result['name'] + '_min')

            if request.GET.get('custom'):
                form=SOPlotUpdateForm(request.GET, variable_choices=variable_choices)
            else:
                form=SOPlotUpdateForm(variable_choices=variable_choices, initial={'variables' : range(len(variable_choices))})

            output['form'] = form

            if form.is_valid():
                variables = map(int,form.cleaned_data['variables'])
                log = form.cleaned_data['logarithmic']
                legend = form.cleaned_data['legend']
                grid = form.cleaned_data['grid']
                fontsize = form.cleaned_data['fontsize']
            else:
                variables=range(len(variable_choices))
                log=False
                legend=True
                grid=True
                fontsize = '12'

            #construct the string to load the image file
            img_string = '?variables=' + str(variables).strip('[').rstrip(']').replace(' ', '')
            img_string += '&name=plot'
            if log:
                img_string += '&log=true'
            if legend:
                img_string += '&legend=true'
            if grid:
                img_string += '&grid=true'
            if fontsize:
                img_string += '&fontsize=' + str(fontsize)

            output['img_string']=img_string
            return output
        else:
            return {}

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

        elif page_name == 'plot':
            return self.get_progress_plot(request)


    def get_progress_plot(self, request):
        """Return the plot image for the progress of a single sensitivity optimization parameter"""

        results = self.copasi_model.get_so_results()

        #Get parameter names, min and max
        variable_choices = []
        for result in results:
            variable_choices.append(result['name'] + '_max')
            variable_choices.append(result['name'] + '_min')

        #Look at the GET data to see what chart options have been set:
        get_variables = request.GET.get('variables','')
        log = request.GET.get('log', 'false')
        legend = request.GET.get('legend', 'false')
        grid = request.GET.get('grid', 'false')
        fontsize = int(request.GET.get('fontsize', '12'))

        #Check to see if we should return as an attachment in .png or .svg or .pdf
        download_png = 'download_png' in request.POST
        download_svg = 'download_svg' in request.POST
        download_pdf = 'download_pdf' in request.POST

        try:
            variables = map(int, get_variables.split(','))
            assert max(variables) < len(variable_choices)
        except:
            #raise
            variables = range(len(results))

        matplotlib.rc('font', size=fontsize)
        fig = plt.figure()
    #        plt.title(job.name + ' (' + str(job.runs) + ' repeats)', fontsize=12, fontweight='bold')
        plt.xlabel('Iterations')
        plt.ylabel('Optimization value')

        color_list = ['red', 'blue', 'green', 'cyan', 'magenta', 'yellow', 'black']

        j=0 #used to keep cycle through colors in order
        jobs = CondorJob.objects.filter(subtask__task=self.task).order_by('id')
        for i in variables:
            #Go through each result and plot the progress
            label = variable_choices[i]

            #Check if we're plotting a min or a max. Min will be all even numbers, max all odd
            file_index = int(math.floor(i/2))
            filename = os.path.join(self.task.directory, jobs.get(process_id=i).job_output)
            #log.debug("filename: %s"%filename)
            all_evals=[]
            all_values=[]
            linenumber=0
            #Go through line by line; lines repeat every 4th line
            for line in open(filename, 'r'):
                if linenumber%4 == 0:
                    pass
                elif linenumber%4 == 1:
                    evals = int(line.split()[2]) # Extract number from 'Evals = n'
                    all_evals.append(evals)
                elif linenumber%4 == 2:
                    pass
                    #time = float(line.split()[2])
                elif linenumber%4 == 3:
                    value = float(line)
                    all_values.append(value)

                linenumber += 1
            #Plot the progress
            plt.plot(all_evals, all_values, lw=1, label=label, color=color_list[j%len(color_list)])

            j+=1
        #Set a logarithmic scale if requested
        if log != 'false':
            plt.yscale('log')
        if legend != 'false':
            plt.legend(loc=0, bbox_to_anchor=(1,1), prop={'size':fontsize} )    #loc value is updated by HB from 0. Also bbox.... option included to move the location of legend.
        if grid != 'false':
            plt.grid(True)

        plt.show()

        #Remove spaces from the task name for saving
        name = self.task.name.replace(' ', '_')
        if download_png:
            #response = HttpResponse(mimetype='image/png', content_type='image/png')
            #above line is modified by HB as follows
            response = HttpResponse(content_type='image/png')
            fig.savefig(response, format='png', transparent=False, dpi=120)
            response['Content-Disposition'] = 'attachment; filename=%s.png' % name

        elif download_svg:
            buf = io.BytesIO()
            fig.savefig(buf, format='svg', transparent=False, dpi=120)
            response = HttpResponse(buf.getvalue(), content_type='image/svg')
            response['Content-Disposition'] = 'attachment; filename=%s.svg' % name


        elif download_pdf:
            buf = io.BytesIO()
            fig.savefig(buf, format='pdf', transparent=False, dpi=120)
            response = HttpResponse(buf.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=%s.pdf' % name

        else:
            response = HttpResponse(content_type='image/png')
            fig.savefig(response, format='png', transparent=False, dpi=120)
        return response

#form to update the SO progress plots
class SOPlotUpdateForm(forms.Form):
    """Form containing controls to update plots"""

    def __init__(self, *args, **kwargs):
        variables = kwargs.pop('variable_choices', [])
        variable_choices = []
        for i in range(len(variables)):
            variable_choices.append((i, variables[i]))

        super(SOPlotUpdateForm, self).__init__(*args, **kwargs)
        self.fields['variables'].choices = variable_choices

    legend = forms.BooleanField(label='Show figure legend', required=False, initial=True)
    grid = forms.BooleanField(label='Show grid', required=False, initial=True)
    logarithmic = forms.BooleanField(label='Logarithmic scale', required=False)
    variables = forms.MultipleChoiceField(choices=(), widget=forms.CheckboxSelectMultiple(), required=True)
    fontsize = forms.IntegerField(label='Font size', required=False, initial='12')
    #Add the name=plot parameter to the GET data so we get the right page back
    name = forms.CharField(widget=forms.widgets.HiddenInput, required=False, initial='plot')
