#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
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
from copasi_model import SSCopasiModel # Use the task-specific copasi model in this directory
import os, math
import logging
from django.http.response import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from cloud_copasi.condor import condor_spec
from string import Template
from cloud_copasi.web_interface.task_plugins import load_balancing
log = logging.getLogger(__name__)

os.environ['HOME'] = settings.STORAGE_DIR #This needs to be set to a writable directory
import matplotlib
matplotlib.use('Agg') #Use this so matplotlib can be used on a headless server. Otherwise requires DISPLAY env variable to be set.
import matplotlib.pyplot as plt
from matplotlib.pyplot import annotate


internal_type = ('stochastic_simulation', 'Stochastic simulation')

class TaskForm(BaseTaskForm):
    #Any extra fields for the task submission form
    skip_load_balancing_step = forms.BooleanField(required=False, help_text='Select this to skip the automatic load balancing step, and make the run time of each parallel job as short as possible. <span class="bold">Use with caution! This has the potential to overload the Condor system with huge numbers of parallel jobs.</span> Not applicable for some job types - see documentation for further details.')
    repeats = forms.IntegerField(required=True, min_value=1, help_text='The number of repeats to perform')

class TaskPlugin(BaseTask):
    
    subtasks = 2

    def __init__(self, task):
        self.use_load_balancing = not task.get_custom_field('skip_load_balancing')
        
        if self.use_load_balancing:
            self.subtasks = 3
        else:
            self.subtasks = 2
            task.set_custom_field('repeats_per_job', 1)
            
        super(TaskPlugin, self).__init__(task)
        
        self.copasi_model = SSCopasiModel(os.path.join(self.task.directory, self.task.original_model))
        self.repeats = self.task.get_custom_field('repeats')

    def validate(self):
        #TODO:Abstract this to a new COPASI class in this plugin package
        return self.copasi_model.is_valid('SS')

    def initialize_subtasks(self):
        #Create new subtask objects, and save them
        
        #Create the load balancing module
        self.create_new_subtask('lb')
        
        #The main module
        self.create_new_subtask('main')
        #And a subtask to process any results
        self.create_new_subtask('process', local=False)
        
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
        #Prepare the necessary files to run on condor
        
        filename = self.copasi_model.prepare_ss_load_balancing(self.repeats)
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
                                                                 copasi_binary=copasi_binary,
                                                                 copasi_file=filename,
                                                                 )
        load_balancing_script_filename = 'load_balance.sh'
        load_balancing_file = open(os.path.join(self.task.directory, load_balancing_script_filename), 'w')
        load_balancing_file.write(load_balancing_script_string)
        load_balancing_file.close()
        
        
        load_balancing_condor_template = Template(condor_spec.condor_string_header + condor_spec.load_balancing_spec_string)
        load_balancing_condor_string = load_balancing_condor_template.substitute(pool_type=self.task.condor_pool.pool_type,
                                                                   pool_address = self.task.condor_pool.address,
                                                                   script = load_balancing_script_filename,
                                                                   copasi_binary=settings.COPASI_LOCAL_BINARY,
                                                                   arguments = str(timeout),
                                                                   copasi_file = (filename),
                                                                   rank=rank,
                                                                   )
        #write to the condor file
        condor_file = open(os.path.join(self.task.directory, 'load_balancing.job'), 'w')
        condor_file.write(load_balancing_condor_string)
        condor_file.close()
        
        subtask=self.get_subtask(1)
        
        subtask.spec_file = 'load_balancing.job'
        subtask.status = 'waiting'
        subtask.save()
        
        return subtask
        
    def process_main_subtask(self):
        #Get the first subtask
        if self.use_load_balancing:
            subtask = self.get_subtask(2)
        else:
            subtask = self.get_subtask(1)
        
        #If no load balancing step required:
        model_files = self.copasi_model.prepare_so_task()
        
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
        
        
        #Go through and collate the results
        #This is a computationally simple task, so we will run locally, not remotely
        
        directory = self.task.directory        
        
        original_subtask = self.get_subtask(1)
        
        output_filename = 'output_1.%d.txt'
        
        
        results = self.copasi_model.get_so_results(save=True)
        log.debug('Results:')
        log.debug(results)
        
        subtask.task.set_custom_field('results_file', 'results.txt')
        
        log.debug('Setting subtask as finished')
        subtask.status = 'finished'
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
        get_variables = request.GET.get('variables')
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
            raise
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
            plt.legend(loc=0, prop={'size':fontsize} )
        if grid != 'false':
            plt.grid(True)
           
        plt.show()
           
        #Remove spaces from the task name for saving
        name = self.task.name.replace(' ', '_')
        if download_png:    
            response = HttpResponse(mimetype='image/png', content_type='image/png')
            fig.savefig(response, format='png', transparent=False, dpi=120)
            response['Content-Disposition'] = 'attachment; filename=%s.png' % name
        elif download_svg:
            response = HttpResponse(mimetype='image/svg', content_type='image/svg')
            fig.savefig(response, format='svg', transparent=False, dpi=120)
            response['Content-Disposition'] = 'attachment; filename=%s.svg' % name
        elif download_pdf:
            response = HttpResponse(mimetype='application/pdf', content_type='application/pdf')
            fig.savefig(response, format='pdf', transparent=False, dpi=120)
            response['Content-Disposition'] = 'attachment; filename=%s.pdf' % name
        else:    
            response = HttpResponse(mimetype='image/png', content_type='image/png')
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
