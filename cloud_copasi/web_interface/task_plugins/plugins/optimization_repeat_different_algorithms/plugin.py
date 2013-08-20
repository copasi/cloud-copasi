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
from copasi_model import ODCopasiModel # Use the task-specific copasi model in this directory
import os, math
import logging
from django.http.response import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from cloud_copasi.condor import condor_spec
from string import Template
from cloud_copasi.web_interface.task_plugins import load_balancing
import re
from django.utils import html
from django.utils.safestring import mark_safe
log = logging.getLogger(__name__)

os.environ['HOME'] = settings.STORAGE_DIR #This needs to be set to a writable directory
import matplotlib
matplotlib.use('Agg') #Use this so matplotlib can be used on a headless server. Otherwise requires DISPLAY env variable to be set.
import matplotlib.pyplot as plt
from matplotlib.pyplot import annotate


internal_type = ('optimization_repeat_different_algorithms', 'Optimization repeat with different algorithms')


algorithms = []
algorithms.append({
    'prefix': 'current_solution_statistics',
    'name': 'Current Solution Statistics',
    'params': []
})

algorithms.append({
    'prefix': 'genetic_algorithm',
    'name': 'Genetic Algorithm',
    #params = (prefix, name, default, type, min, max)
    'params': [('number_of_generations', 'Number of generations', 200, int, 1, None),
               ('population_size', 'Population size', 20, int, 1, None),
               ('random_number_generator', 'Random number generator', 1, int, 0, None),
               ('seed', 'Seed', 0, float, 0, None),
               ]
})
algorithms.append({
    'prefix': 'genetic_algorithm_sr',
    'name': 'Genetic Algorithm SR',
    'params': [('number_of_generations', 'Number of generations', 200, int, 1, None),
               ('population_size', 'Population size', 20, int, 1, None),
               ('random_number_generator', 'Random number generator', 1, int, 0, None),
               ('seed', 'Seed', 0, float, 0, None),
               ('pf', 'Pf', 0.475, float, 0, 1),
               ]
})
algorithms.append({
    'prefix': 'hooke_and_jeeves',
    'name': 'Hooke & Jeeves',
    'params': [('iteration_limit', 'Iteration limit', 50, int, 1, None),
               ('tolerance', 'Tolerance', 1e-5, float, 0, None),
               ('rho', 'Rho', 0.2, float, 0, 1),
               ]
})
algorithms.append({
    'prefix': 'levenberg_marquardt',
    'name': 'Levenberg-Marquardt',
    'params': [('iteration_limit', 'Iteration limit', 50, int, 1, None),
               ('tolerance', 'Tolerance', 1e-5, float, 0, None),
               ]

})
algorithms.append({
    'prefix': 'evolutionary_programming',
    'name': 'Evolutionary Programming',
    'params': [('number_of_generations', 'Number of generations', 200, int, 1, None),
               ('population_size', 'Population size', 20, int, 1, None),
               ('random_number_generator', 'Random number generator', 1, int, 0, None),
               ('seed', 'Seed', 0, float, 0, None),
               ]
    
})
algorithms.append({
    'prefix': 'random_search',
    'name': 'Random Search',
    'params': [('no_of_iterations', 'Number of iterations', 10000, int, 1, None),
               ('random_number_generator', 'Random number generator', 1, int, 0, None),
               ('seed', 'Seed', 0, float, 0, None),
              ]

    
})
algorithms.append({
    'prefix': 'nelder_mead',
    'name': 'Nelder-Mead',
    'params': [('iteration_limit', 'Iteration limit', 200, int, 1, None),
               ('tolerance', 'Tolerance', 1e-5, float, 0, None),
               ('scale', 'Scale', 10, float, 0, None),
               ]

    
})
algorithms.append({
    'prefix': 'particle_swarm',
    'name': 'Particle Swarm',
    'params': [('iteration_limit', 'Iteration limit', 2000, int, 1, None),
               ('swarm_size', 'Swarm size', 200, int, 1, None),
               ('std_deviation', 'Standard deviation', 1e-6, float, 0, None),
               ('random_number_generator', 'Random number generator', 1, int, 0, None),
               ('seed', 'Seed', 0, float, 0, None),
               ]

})
algorithms.append({
    'prefix': 'praxis',
    'name': 'Praxis',
     'params': [('tolerance', 'Tolerance', 1e-5, float, 0, None),
       ]
})
algorithms.append({
    'prefix': 'truncated_newton',
    'name': 'Truncated Newton',
    'params' : []
})
algorithms.append({
    'prefix': 'simulated_annealing',
    'name': 'Simulated Annealing',
    'params' : [('start_temperature', 'Start temperature', 1, float, 0, None),
                ('cooling_factor', 'Cooling factor', 0.85, float, 0, None),
                ('tolerance', 'Tolerance', 1e-6, float, 0, None),
                ('random_number_generator', 'Random number generator', 1, int, 0, None),
                ('seed', 'Seed', 0, float, 0, None),
                ]
})
algorithms.append({
    'prefix': 'evolution_strategy',
    'name': 'Evolution Strategy',
    'params': [('number_of_generations', 'Number of generations', 200, int, 1, None),
               ('population_size', 'Population size', 20, int, 1, None),
               ('random_number_generator', 'Random number generator', 1, int, 0, None),
               ('seed', 'Seed', 0, float, 0, None),
               ('pf', 'Pf', 0.475, float, 0, 1),
               ]

})
algorithms.append({
    'prefix': 'steepest_descent',
    'name': 'Steepest Descent',
    'params': [('iteration_limit', 'Iteration limit', 100, int, 1, None),
               ('tolerance', 'Tolerance', 1e-6, float, 0, None),
               ]

})    
     

class SelectButtonWidget(forms.Widget):
    def render(self, name, value, attrs=None):
        return mark_safe('<input type="button" name="select_all" value="Select all" onclick="select_all_selectors();"></input><input type="button" name="select_none" value="Select none" onclick="deselect_all_selectors();"></input>')


class SelectButtonField(forms.Field):
    def __init__(self, *args, **kwargs):
        if not kwargs:
            kwargs = {}
        kwargs["widget"] = SelectButtonWidget

        super(SelectButtonField, self).__init__(*args, **kwargs)

    def clean(self, value):
        return value


class TaskForm(BaseTaskForm):
    
    select_all = SelectButtonField(label='Algorithms')
    
    
    def __init__(self, *args, **kwargs):
        try:
            super(TaskForm, self).__init__(*args, **kwargs)
            
            for algorithm in algorithms:
                self.fields[algorithm['prefix']] = forms.BooleanField(required=False,
                                                                      label=algorithm['name'],
                                                                      widget=forms.CheckboxInput(attrs={'class':'form-group selector',
                                                                                                        'onclick': "toggle('%s')" % algorithm['prefix']}))
                for prefix, name, value, typeof, minimum, maximum in algorithm['params']:
                    if typeof==int:
                        field_class=forms.IntegerField
                    else:
                        field_class=forms.FloatField
                        
                    field = field_class(required=False,
                                       label=name,
                                       min_value=minimum,
                                       max_value=maximum,
                                       initial=value,
                                       widget=forms.TextInput(attrs={'class':'form-group hidden_form %s' % algorithm['prefix']})
                                       )
                    
                    self.fields[algorithm['prefix'] + '_' + prefix] = field

        except Exception, e:
            log.debug(e)

    

    
    def clean(self):
        
        cleaned_data = super(TaskForm, self).clean()
        
        #Raise a validation error if fields are blank when checkbox is selected
        
        for algorithm in algorithms:
            if cleaned_data.get(algorithm['prefix']) == True:
                for prefix, name, value, typeof, minimum, maximum in algorithm['params']:
                    clean_value = cleaned_data.get(algorithm['prefix'] + '_' + prefix, None)
                    if clean_value == None:
                        msg = 'This field is required when %s is selected' % algorithm['name']
                        self._errors[algorithm['prefix'] + '_' + prefix] = self.error_class([msg])
                        del cleaned_data[algorithm['prefix'] + '_' + prefix]
                        
class TaskPlugin(BaseTask):
    
    subtasks = 2

    def __init__(self, task):
        self.subtasks = 2
            
        super(TaskPlugin, self).__init__(task)
        
        self.copasi_model = ODCopasiModel(os.path.join(self.task.directory, self.task.original_model))
    def validate(self):
        #TODO:Abstract this to a new COPASI class in this plugin package
        return self.copasi_model.is_valid('OD')

    def initialize_subtasks(self):
        #Create new subtask objects, and save them
        #The main module
        self.create_new_subtask('main')
        #And a subtask to process any results
        self.create_new_subtask('process', local=True)
        
    def prepare_subtask(self, index):
        """Prepare the indexed subtask"""
        
        if index == 1:
            return self.process_main_subtask()
        
        elif index == 2:
            return self.process_results_subtask()
        else:
            raise Exception('No subtasks remaining')


        
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
                except Exception, e:
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
        model_files = self.copasi_model.prepare_or_jobs(self.repeats, repeats_per_job, subtask.index)
        
        condor_pool = self.task.condor_pool
        
        condor_job_file = self.copasi_model.prepare_or_condor_job(condor_pool.pool_type,
                                                                  condor_pool.address,
                                                                  len(model_files),
                                                                  subtask.index,
                                                                  rank='')
        
        log.debug('Prepared copasi files %s'%model_files)
        log.debug('Prepared condor job %s' %condor_job_file)
        
        model_count = len(model_files)
        self.task.set_custom_field('model_count', model_count)
        
        
        subtask.spec_file = condor_job_file
        subtask.status = 'ready'
        subtask.save()
        
        return subtask
        
        
    def process_results_subtask(self):
        subtask=self.get_subtask(2)
        assert isinstance(subtask, Subtask)
        
        
        #Go through and collate the results
        #This is reasonably computationally simple, so we run locally
                
        directory = self.task.directory        
        
        
        if self.use_load_balancing:
            main_subtask = self.get_subtask(2)
            subtask = self.get_subtask(3)
        else:
            main_subtask = self.get_subtask(1)
            subtask = self.get_subtask(2)
        
        main_jobs = CondorJob.objects.filter(subtask=main_subtask)
        
        results_files = [job.job_output for job in main_jobs]
        
        self.copasi_model.process_or_results(results_files)
                
        subtask.status = 'finished'
        subtask.save()
        
        subtask.task.results_view=False
        subtask.task.save()
        
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

    

