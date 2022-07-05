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
from web_interface.task_plugins.plugins.profile_likelihood.copasi_model import PLCopasiModel_BasiCO # Use the task-specific copasi model in this directory
import os, math, pandas
from scipy import stats
import scipy as sp
import logging
from django.http.response import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from cloud_copasi.condor import condor_spec
from string import Template
from web_interface.task_plugins import load_balancing
import re
import datetime
from django.utils import timezone

log = logging.getLogger(__name__)
slog = logging.getLogger("special")

os.environ['HOME'] = settings.STORAGE_DIR #This needs to be set to a writable directory
import matplotlib
matplotlib.use('Agg') #Use this so matplotlib can be used on a headless server. Otherwise requires DISPLAY env variable to be set.
import matplotlib.pyplot as plt
import io
import zipfile
from matplotlib.pyplot import annotate

internal_type = ('profile_likelihood', 'Profile Likelihood')

class TaskForm(BaseTaskForm):
    #Any extra fields for the task submission form
    parameter_estimation_data = forms.FileField(required=True, help_text='Select either a single data file, or if more than one data file is required, upload a .zip file containing multiple data files.')

class TaskPlugin(BaseTask):

    subtasks = 2

    def __init__(self, task):
        #self.use_load_balancing = not task.get_custom_field('skip_load_balancing_step')
        self.data_files = task.get_custom_field('data_files')


        # if self.use_load_balancing:
        #     self.subtasks = 3
        # else:
        #     self.subtasks = 2
        #     task.set_custom_field('repeats_per_job', 1)
        #     task.save()

        super(TaskPlugin, self).__init__(task)

        self.copasi_model = PLCopasiModel_BasiCO(os.path.join(self.task.directory, self.task.original_model))

    def validate(self):
        #TODO:Abstract this to a new COPASI class in this plugin package
        valid_result = self.copasi_model.is_valid('PL')
        slog.debug("Is model valid: {}".format(valid_result))
        return valid_result

    def initialize_subtasks(self):
        #Create new subtask objects, and save them

        # #Create a task to generate PL files for each Parameters
        # self.create_new_subtask('PlFiles', local=True)
        #Create a task to submit jobs on remote submit node
        self.create_new_subtask('main')

        #And a subtask to process results locally (on web server)
        self.create_new_subtask('process', local=True)
        # self.task.result_download = True
        self.task.save()

    def prepare_subtask(self, index):
        """Prepare the indexed subtask"""
        if index == 1:
            return self.process_main_subtask()

        elif index == 2:
            return self.process_results_subtask()

        # elif index == 3:
            # return self.process_results_subtask()
        else:
            raise Exception('No subtasks remaining')

    def process_main_subtask(self):
        subtask = self.get_subtask(1)

        model_files, file_param_assign = self.copasi_model.prepare_pl_files(subtask.index)
        # slog.debug("model files: {}".format(model_files))

        condor_pool = self.task.condor_pool

        condor_job_file = self.copasi_model.prepare_pl_condor_job(condor_pool.pool_type, condor_pool.address, len(model_files), subtask.index, self.data_files, rank='')

        model_count = len(model_files)
        self.task.set_custom_field('model_count', model_count)

        subtask.spec_file = condor_job_file
        subtask.status = 'ready'
        subtask.save()


        return subtask

    def process_results_subtask(self):
        main_subtask = self.get_subtask(1)
        subtask = self.get_subtask(2)

        assert isinstance(subtask, Subtask)

        subtask.start_time = timezone.localtime()
        temp_start_time = subtask.start_time

        slog.debug("============== temp_start_time: ")
        slog.debug(subtask.start_time)

        directory = self.task.directory

        main_jobs = CondorJob.objects.filter(subtask=main_subtask)
        results_files = [job.job_output for job in main_jobs]
        slog.debug("results_files: {}".format(results_files))

        param_to_plot = self.copasi_model.process_original_pl_model()

        slog.debug("param_to_plot: {}".format(param_to_plot))

        self.task.save()
        subtask.status = 'finished'
        subtask.finish_time = timezone.localtime()
        temp_finish_time = subtask.finish_time

        time_delta = temp_finish_time - temp_start_time

        slog.debug("Time Delta: {}".format(time_delta))
        subtask.set_run_time(time_delta)

        subtask.save()

        return subtask

    def read_xy_data(self, data_file_path):
        """Reading simulation data from output_1.x.txt files"""

        data_file = open(data_file_path, "r")
        lines = data_file.readlines()

        x = []
        y = []
        index = 0

        for line in lines:
            if index == 0:
                index += 1
            else:
                values = line.split('\t')
                x.append(float(values[0]))
                y.append(float(values[1].strip('\n')))

        return x, y

    def get_pl_plot(self, request, param_to_plot):
        """ generate plot and display it on the front interface. """
        total_params = len(param_to_plot)       #total number of parameters
        try:
            logX = request.GET.get('logX', 'false')
            logY = request.GET.get('logY', 'false')
            legend = request.GET.get('legend', 'false')
            grid = request.GET.get('grid', 'false')

            # slog.debug("log: {}".format(log))

            # Check to see if we should return as an attachment in .png or .svg or .pdf
            download_png = 'download_png' in request.POST
            download_svg = 'download_svg' in request.POST
            download_pdf = 'download_pdf' in request.POST

            plt.switch_backend('Agg')
            plot_list = []
            rows = math.ceil(total_params/4.0)

            if total_params < 4:
                cols = total_params
            else:
                cols = 4

            width = 3 * cols
            height = 4 * rows
            fig, ax = plt.subplots(rows, cols, squeeze=False, figsize=(width,height), sharey=True)
            # fig, ax = plt.subplots(rows, cols, figsize=(9,11), sharey=True)
            # ax = ax.flat

            plt.subplots_adjust(wspace=0.4, hspace=0.5)

            for i in range(total_params):
                read_file_name = 'output_1.%d.txt' %i
                read_file = os.path.join(self.task.directory, read_file_name)
                poi_data = param_to_plot[i]

                x, y = self.read_xy_data(read_file)     #reading simulation data from output_1.x.txt files
                min_val = min(y)    #reading minimum value of y to set it on the y-axis
                max_val = max(y)    #reading maximum value of y to set it on the y-axis


                #Plot settings
                if rows != 1:
                    a = int(i/(rows-1))
                else:
                    a = 0
                b = i%(cols)

                if grid != 'false':
                    ax[a, b].grid(color='grey', linestyle='--', linewidth='0.1')
                else:
                    ax[a, b].grid(color='grey', linestyle='--', linewidth='0')

                ax[a, b].plot(x,y, marker = 'o')
                ax[a, b].plot(poi_data[1], poi_data[2], 'ro', ms = 7)
                ax[a, b].axhline(y = poi_data[2], color='red', linestyle='dotted')   #plotting a horizontal line for SoS
                ax[a, b].set_xlabel('%s' %poi_data[0])

                if logX != 'false':
                    ax[a, b].set_xscale('log')

                if logY != 'false':
                    ax[a, b].set_yscale('log')

                # for xy coordinates in poi_data:
                #SoS_x = "{:.1f}".format(poi_data[1])
                #SoS_y = "{:.1f}".format(poi_data[2])
                #displaying the coordinate value of best solution
                # ax[i].annotate(text = "(%s, %s)" %(SoS_x, SoS_y), xy = (poi_data[1], poi_data[2]), rotation=45)

                #estimating chi-square value fitting one parameter
                c1 = sp.stats.chi2.isf(0.05, 1, loc = 0, scale = 1)
                t1 = poi_data[2] * math.exp(c1/total_params)      #threshold value for 95% confidence
                ax[a, b].axhline(y = t1, color='blue', linestyle='dotted')   #plotting a horizontal line for SoS

                #estimating chi-square value fitting n parameter
                c2 = sp.stats.chi2.isf(0.05, total_params, loc = 0, scale = 1)
                t2 = poi_data[2] * math.exp(c2/total_params)      #threshold value for 95% confidence
                ax[a, b].axhline(y = t2, color='green', linestyle='solid')   #plotting a horizontal line for SoS

                #setting the y-axis limit
                # ax[a, b].set_ylim(min_val * 0.07, t2*2.1)
                if max_val >= 1e90:
                    ax[a, b].set_ylim(min_val*0.05, t2*1.2)
                else:
                    ax[a, b].set_ylim(min_val*0.05, max_val*1.5)

            # When total parameters are not divisible by 4 (meaning that they need to be fixed in next row)
            # also when the loop value is the last parameter value
            if (total_params > 4):   #when parameters are greater than the size of one row
                if (total_params % 4 != 0) and (i == total_params -1):

                    #subplots that are valid and have data
                    valid_subplots = total_params % 4
                    slog.debug("valid_subplots: {}".format(valid_subplots))

                    empty_subplots = 4 - valid_subplots
                    for i in range(empty_subplots):
                        del_plot_idx = i + valid_subplots
                        fig.delaxes(ax[a, del_plot_idx])


            #plot labeling and saving
            plt.suptitle("Profile Likelihood", y =0.99)
            fig.supylabel("Sum of Squares")
            fig.tight_layout()

            name = self.task.name.replace(' ', '_')
            if download_png:
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

        except Exception as e:
            slog.exception(e)
            raise e

    def get_results_view_template_name(self, request):
        """Return a string with the HTML code to be used in the task results view page
        """
        # Get the name of the page we're displaying. If not specified, assume main
        page_name = request.GET.get('name', 'main')

        if page_name == 'main':
            return self.get_template_name('pl_sub_plots')

        else:
            return ''

    def get_results_view_data(self, request):
        page_name = request.GET.get('name', 'main')
        if page_name == 'main':
            model = self.copasi_model

            try:
                assert request.GET.get('custom') == 'true'
                form = PlotUpdateForm(request.GET)
            except:
                form = PlotUpdateForm(initial={'key':'value'})

            if form.is_valid():
                logX = form.cleaned_data['logarithmicX']
                logY = form.cleaned_data['logarithmicY']
                legend = form.cleaned_data['legend']
                grid = form.cleaned_data['grid']
            else:
                logX = False
                logY = False
                legend = True
                grid = True


            # construct the string to load the image file
            img_string = '?name=plot'
            if logX:
                img_string += '&logX=true'
            if logY:
                img_string += '&logY=true'
            if legend:
                img_string += '&legend=true'
            if grid:
                img_string += '&grid=true'

            output = {'form': form, 'img_string': img_string}
            slog.debug("output: {}".format(output))

            return output

    def get_results_download_data(self, request):

        page_name = request.GET.get('name', 'main')

        if page_name == 'main':
            zip_file_name = "Results.zip"
            filename = os.path.join(self.task.directory, zip_file_name)
            directory = self.task.directory

            compile_string = re.compile('output_[0-9].[0-9]*.txt')

            with zipfile.ZipFile(filename, 'w') as zip:
                for path, directory, files in os.walk(directory):
                    for file in files:
                        name = compile_string.match(file)
                        if name != None:
                            file_to_write = os.path.join(self.task.directory, file)
                            zip.write(file_to_write, file)
                zip.close()

            result_file = open(filename, 'rb')
            response = HttpResponse(result_file, content_type='application/x-zip-compressed')
            response['Content-Disposition'] = 'attachment; filename=' + zip_file_name
            response['Content-Length'] = os.path.getsize(filename)

            return response

        elif page_name == 'plot':
            param_to_plot = self.copasi_model.process_original_pl_model()
            slog.debug("page_name: {}".format(page_name))
            slog.debug("get_results_download_data")
            return self.get_pl_plot(request, param_to_plot)

class PlotUpdateForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(PlotUpdateForm, self).__init__(*args, **kwargs)

    legend = forms.BooleanField(label="Show figure legend", required=False, initial=True)
    grid = forms.BooleanField(label="Show grid", required=False, initial=True)
    logarithmicX = forms.BooleanField(label="Log Scale X", required = False)
    logarithmicY = forms.BooleanField(label="Log Scale Y", required = False)
