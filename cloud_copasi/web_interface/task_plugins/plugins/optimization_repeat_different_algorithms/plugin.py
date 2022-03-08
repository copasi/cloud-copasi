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
from django.forms import Form, widgets
from django import forms
from cloud_copasi import settings
from cloud_copasi.web_interface.task_plugins.plugins.optimization_repeat_different_algorithms.copasi_model import ODCopasiModel, ODCopasiModel_BasiCO # Use the task-specific copasi model in this directory
import os, math
import logging
from django.http.response import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from cloud_copasi.condor import condor_spec
from string import Template
from cloud_copasi.web_interface.task_plugins import load_balancing
import re
import datetime
from django.utils import html
from django.utils.safestring import mark_safe
from django.forms.utils import ErrorList
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
    'params': [('no_of_generations', 'Number of generations', 200, int, 1, None),
               ('population_size', 'Population size', 20, int, 1, None),
               ('random_number_generator', 'Random number generator', 1, int, 0, None),
               ('seed', 'Seed', 0, int, 0, None),
               ]
})
algorithms.append({
    'prefix': 'genetic_algorithm_sr',
    'name': 'Genetic Algorithm SR',
    'params': [('no_of_generations', 'Number of generations', 200, int, 1, None),
               ('population_size', 'Population size', 20, int, 1, None),
               ('random_number_generator', 'Random number generator', 1, int, 0, None),
               ('seed', 'Seed', 0, int, 0, None),
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
    'params': [('no_of_generations', 'Number of generations', 200, int, 1, None),
               ('population_size', 'Population size', 20, int, 1, None),
               ('random_number_generator', 'Random number generator', 1, int, 0, None),
               ('seed', 'Seed', 0, int, 0, None),
               ]

})
algorithms.append({
    'prefix': 'random_search',
    'name': 'Random Search',
    'params': [('no_of_iterations', 'Number of iterations', 10000, int, 1, None),
               ('random_number_generator', 'Random number generator', 1, int, 0, None),
               ('seed', 'Seed', 0, int, 0, None),
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
               ('seed', 'Seed', 0, int, 0, None),
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
                ('seed', 'Seed', 0, int, 0, None),
                ]
})
algorithms.append({
    'prefix': 'evolution_strategy',
    'name': 'Evolution Strategy',
    'params': [('no_of_generations', 'Number of generations', 200, int, 1, None),
               ('population_size', 'Population size', 20, int, 1, None),
               ('random_number_generator', 'Random number generator', 1, int, 0, None),
               ('seed', 'Seed', 0, int, 0, None),
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
    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe('<input type="button" name="select_all" value="Select All" onclick="select_all_selectors();"></input><input type="button" name="select_none" value="Select None" onclick="deselect_all_selectors();"></input>')


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
                                                                      widget=forms.CheckboxInput(attrs={'class':'form-group selector'}))
                                                                                                       
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

        except Exception as e:
            log.debug(e)




    def clean(self):

        cleaned_data = super(TaskForm, self).clean()

        #Raise a validation error if fields are blank when checkbox is selected
        at_least_one_selected = False

        for algorithm in algorithms:
            if cleaned_data.get(algorithm['prefix']) == True:
                at_least_one_selected = True
                for prefix, name, value, typeof, minimum, maximum in algorithm['params']:
                    clean_value = cleaned_data.get(algorithm['prefix'] + '_' + prefix, None)
                    if clean_value == None:
                        msg = 'This field is required when %s is selected' % algorithm['name']
                        self._errors[algorithm['prefix'] + '_' + prefix] = self.error_class([msg])
                        del cleaned_data[algorithm['prefix'] + '_' + prefix]

        if not at_least_one_selected:
            self._errors['__all__'] = ErrorList(['At least one algorithm must be selected'])

        return cleaned_data


class TaskPlugin(BaseTask):

    subtasks = 2

    def __init__(self, task):
        self.subtasks = 2

        super(TaskPlugin, self).__init__(task)
        check.debug('~~~~~~~~~~~~ Running LXML Implementation')
        self.copasi_model = ODCopasiModel(os.path.join(self.task.directory, self.task.original_model))
        #check.debug("+++++++++++ Running BasiCO implementation.")
        #self.copasi_model = ODCopasiModel_BasiCO(os.path.join(self.task.directory, self.task.original_model))


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

        #Build a list of the submitted algorithms
        subtask = self.get_subtask(1)

        submitted_algorithms = []
        for algorithm in algorithms:
            if self.task.get_custom_field(algorithm['prefix']):
                params = {}
                for prefix, name, value, type, minimum, maximum in algorithm['params']:
                    params[prefix] = str(self.task.get_custom_field(algorithm['prefix'] + '_' + prefix))

                submitted_algorithms.append({'prefix': algorithm['prefix'],
                                             'params': params
                                             })
        #added by HB
        check.debug('submitted_algorithms: ')
        check.debug(submitted_algorithms)

        #If no load balancing step required:
        model_files, output_files = self.copasi_model.prepare_od_jobs(submitted_algorithms)

        condor_pool = self.task.condor_pool

        condor_job_file = self.copasi_model.prepare_or_condor_job(condor_pool.pool_type,
                                                                  condor_pool.address,
                                                                  len(model_files),
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
        subtask=self.get_subtask(2)
        assert isinstance(subtask, Subtask)

        subtask.start_time = timezone.localtime()

        main_subtask = self.get_subtask(1)
        #Go through and collate the results
        #This is reasonably computationally simple, so we run locally

        temp_start_time = subtask.start_time

        directory = self.task.directory

        main_jobs = CondorJob.objects.filter(subtask=main_subtask)

        results_files = [job.job_output for job in main_jobs]

        #Get a list of algorithm names
        algorithm_list = []
        for algorithm in algorithms:
            if self.task.get_custom_field(algorithm['prefix']):
                algorithm_list.append(algorithm['name'])

        self.copasi_model.process_od_results(algorithm_list, results_files)

        subtask.status = 'finished'

        subtask.finish_time = timezone.localtime()

        temp_finish_time = subtask.finish_time


        time_delta = temp_finish_time - temp_start_time

        check.debug("Time Delta: ")
        check.debug(time_delta)
        subtask.set_run_time(time_delta)

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
            results = model.get_od_results()
            best_value=results[1][1]
            return {'results':results, 'best_value':best_value}

    def get_results_download_data(self, request):
        page_name = request.GET.get('name', 'main')
        main_subtask = self.get_subtask(1)
        #Go through and collate the results
        #This is reasonably computationally simple, so we run locally

        main_jobs = CondorJob.objects.filter(subtask=main_subtask)

        results_files = [job.job_output for job in main_jobs]

        #Get a list of algorithm names
        algorithm_list = []
        for algorithm in algorithms:
            if self.task.get_custom_field(algorithm['prefix']):
                algorithm_list.append(algorithm['name'])

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

        elif page_name == 'model':
            index = request.GET.get('index')
            #Name will be an algorithm index
            assert int(index) < len(algorithms)

            index = int(index) - 1 #Account for 1-indexing

            key = self.copasi_model.process_od_results(algorithm_list, results_files, write=False, return_list=True)

            model_index = key[index]

            filename = os.path.join(self.task.directory, 'run_auto_copasi_1.%d.cps'%model_index)
            if not os.path.isfile(filename):
                request.session['errors'] = [('Cannot Return Output', 'There was an internal error processing the results file')]
                return HttpResponseRedirect(reverse_lazy('task_details', kwargs={'task_id':self.task.id}))
            result_file = open(filename, 'r', encoding='UTF-8')
            response = HttpResponse(result_file, content_type='application/xml')
            response['Content-Disposition'] = 'attachment; filename=%s_model.cps' % algorithms[model_index]['prefix']
            response['Content-Length'] = os.path.getsize(filename)

            return response

        elif page_name == 'output':
            index = request.GET.get('index')
            #Name will be an algorithm index
            assert int(index) < len(algorithms)

            index = int(index) - 1 #Account for 1-indexing

            key = self.copasi_model.process_od_results(algorithm_list, results_files, write=False, return_list=True)

            model_index = key[index]

            filename = os.path.join(self.task.directory, 'output_1.%s.txt'%model_index)
            if not os.path.isfile(filename):
                request.session['errors'] = [('Cannot Return Output', 'There was an internal error processing the results file')]
                return HttpResponseRedirect(reverse_lazy('task_details', kwargs={'task_id':self.task.id}))
            result_file = open(filename, 'r')
            response = HttpResponse(result_file, content_type='text/tab-separated-values')
            response['Content-Disposition'] = 'attachment; filename=%s_results.txt' % algorithms[model_index]['prefix']
            response['Content-Length'] = os.path.getsize(filename)

            return response
