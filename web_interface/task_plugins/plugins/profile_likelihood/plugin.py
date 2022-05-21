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

        #added by HB
        slog.debug("---------> self.task.directory: {}".format(self.task.directory))
        slog.debug("---------> self.task.original_model: {}".format(self.task.original_model))

        slog.debug("+++++++++++ Running BasiCO implementation.")
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
        self.task.save()

    def prepare_subtask(self, index):
        """Prepare the indexed subtask"""
        if index == 1:
            # return self.process_plfiles_subtask()
            return self.process_main_subtask()

        elif index == 2:
            # return self.process_main_subtask()
            slog.debug("============== executing process_results_subtask: ")
            return self.process_results_subtask()

        # elif index == 3:
            # return self.process_results_subtask()
        else:
            raise Exception('No subtasks remaining')


    def process_main_subtask(self):
        subtask = self.get_subtask(1)

        model_files, file_param_assign = self.copasi_model.prepare_pl_files(subtask.index)

        slog.debug("model files: {}".format(model_files))

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

        #generating plots and saving in the
        self.generate_plots(param_to_plot)

        self.task.save()
        subtask.status = 'finished'
        subtask.finish_time = timezone.localtime()
        temp_finish_time = subtask.finish_time

        time_delta = temp_finish_time - temp_start_time

        slog.debug("Time Delta: {}".format(time_delta))
        subtask.set_run_time(time_delta)

        self.task.result_download = False
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

    def generate_plots(self, param_to_plot):
        plot_list = []
        rows = math.ceil(len(param_to_plot)/4.0)
        slog.debug("rows: {}".format(rows))

        if len(param_to_plot) < 4:
            cols = len(param_to_plot)
        else:
            cols = 4

        slog.debug("cols: {}".format(cols))
        fig, ax = plt.subplots(rows, cols, figsize=(15,5), sharey=True)
        plt.subplots_adjust(wspace=0.2, hspace=0.2)

        for i in range(len(param_to_plot)):
            read_file_name = 'output_1.%d.txt' %i #update it for the server
            read_file = os.path.join(self.task.directory, read_file_name)

            # plot_file_name = 'output_1.%d' %i + ".png"
            # plot_file = os.path.join(self.task.directory, plot_file_name)
            poi_data = param_to_plot[i]

            slog.debug(" ========== Reading xy data")
            x, y = self.read_xy_data(read_file)     #reading simulation data from output_1.x.txt files
            slog.debug("x: {}".format(x))
            slog.debug("y: {}".format(y))

            min_val = min(y)    #reading minimum value of y to set it on the y-axis
            slog.debug("min_value: {}".format(min_val))

            #Plot settings
            ax[i].grid(color='grey', linestyle='--', linewidth='0.1')
            ax[i].plot(x,y, marker = 'o')
            ax[i].plot(poi_data[1], poi_data[2], 'ro', ms = 7)
            ax[i].axhline(y = poi_data[2], color='red', linestyle='dotted')   #plotting a horizontal line for SoS
            ax[i].set_xlabel('%s' %poi_data[0])

            # for xy coordinates in poi_data:
            #SoS_x = "{:.1f}".format(poi_data[1])
            #SoS_y = "{:.1f}".format(poi_data[2])
            #displaying the coordinate value of best solution
            # ax[i].annotate(text = "(%s, %s)" %(SoS_x, SoS_y), xy = (poi_data[1], poi_data[2]), rotation=45)

            #estimating chi-square value fitting one parameter
            c1 = sp.stats.chi2.isf(0.05, 1, loc = 0, scale = 1)
            print(f"c1: {c1}")
            t1 = poi_data[2] * math.exp(c1/len(param_to_plot))      #threshold value for 95% confidence
            print(f"poi_data[1]: {poi_data[2]}")
            print(math.exp(c1/len(param_to_plot)))
            print(f"t1: {t1}")
            ax[i].axhline(y = t1, color='blue', linestyle='dotted')   #plotting a horizontal line for SoS

            #estimating chi-square value fitting n parameter
            c2 = sp.stats.chi2.isf(0.05, len(param_to_plot), loc = 0, scale = 1)
            print(f"c2: {c2}")
            t2 = poi_data[2] * math.exp(c2/len(param_to_plot))      #threshold value for 95% confidence
            print(f"t2: {t2}")
            ax[i].axhline(y = t2, color='green', linestyle='solid')   #plotting a horizontal line for SoS

            #setting the y-axis limit
            ax[i].set_ylim(min_val * 0.4, t2*1.2)

        #plot labeling and saving
        plt.suptitle("Profile Likelihood")
        fig.supylabel("Sum of Squares")
        plot_file = os.path.join(self.task.directory, 'subplots.png')
        plt.savefig(plot_file)

    def get_pl_plot(self, request, param_to_plot):
        try:
            log = request.GET.get('log', 'false')
            legend = request.GET.get('legend', 'false')
            grid = request.GET.get('grid', 'false')


            # Check to see if we should return as an attachment in .png or .svg or .pdf
            download_png = 'download_png' in request.POST
            download_svg = 'download_svg' in request.POST
            download_pdf = 'download_pdf' in request.POST

            ########### TEST logic added from local implementation #######
            plt.switch_backend('Agg')
            plot_list = []
            rows = math.ceil(len(param_to_plot)/4.0)
            slog.debug("rows: {}".format(rows))
            # print(f"rows: {rows}")

            if len(param_to_plot) < 4:
                cols = len(param_to_plot)
            else:
                cols = 4

            slog.debug("cols: {}".format(cols))
            # print(f"cols: {cols}")
            fig, ax = plt.subplots(rows, cols, figsize=(8,3.2), sharey=True)
            plt.subplots_adjust(wspace=0.2, hspace=0.2)

            for i in range(len(param_to_plot)):
                # print(os.path.dirname(__file__))
                read_file_name = 'output_1.%d.txt' %i #update it for the server
                # read_file = os.path.join(os.path.dirname(__file__), read_file_name)

                read_file = os.path.join(self.task.directory, read_file_name)

                # plot_file_name = 'output_1.%d' %i + ".png"
                # plot_file = os.path.join(self.task.directory, plot_file_name)
                poi_data = param_to_plot[i]

                slog.debug(" ========== Reading xy data")
                # print(" ========== Reading xy data")
                x, y = self.read_xy_data(read_file)     #reading simulation data from output_1.x.txt files
                # x, y = read_xy_data(read_file)     #reading simulation data from output_1.x.txt files
                slog.debug("x: {}".format(x))
                slog.debug("y: {}".format(y))
                # print(f"x: {x}")
                # print(f"y: {y}")

                min_val = min(y)    #reading minimum value of y to set it on the y-axis
                slog.debug("min_value: {}".format(min_val))
                # print(f"min_value: {min_val}")

                #Plot settings
                if grid == True:
                    ax[i].grid(color='grey', linestyle='--', linewidth='0.1')
                else:
                    ax[i].grid(color='grey', linestyle='--', linewidth='0')

                ax[i].plot(x,y, marker = 'o')
                ax[i].plot(poi_data[1], poi_data[2], 'ro', ms = 7)
                ax[i].axhline(y = poi_data[2], color='red', linestyle='dotted')   #plotting a horizontal line for SoS
                ax[i].set_xlabel('%s' %poi_data[0])

                if log == True:
                    ax[i].set_xscale('log')

                # for xy coordinates in poi_data:
                #SoS_x = "{:.1f}".format(poi_data[1])
                #SoS_y = "{:.1f}".format(poi_data[2])
                #displaying the coordinate value of best solution
                # ax[i].annotate(text = "(%s, %s)" %(SoS_x, SoS_y), xy = (poi_data[1], poi_data[2]), rotation=45)

                #estimating chi-square value fitting one parameter
                c1 = sp.stats.chi2.isf(0.05, 1, loc = 0, scale = 1)
                # print(f"c1: {c1}")
                slog.debug("c1: {}".format(c1))
                t1 = poi_data[2] * math.exp(c1/len(param_to_plot))      #threshold value for 95% confidence
                # print(f"poi_data[1]: {poi_data[2]}")
                slog.debug("poi_data[1]: {}".format(poi_data[2]))
                # print(math.exp(c1/len(param_to_plot)))
                slog.debug("math.exp: {}".format(math.exp(c1/len(param_to_plot))))
                # print(f"t1: {t1}")
                slog.debug("t1: {}".format(t1))
                ax[i].axhline(y = t1, color='blue', linestyle='dotted')   #plotting a horizontal line for SoS

                #estimating chi-square value fitting n parameter
                c2 = sp.stats.chi2.isf(0.05, len(param_to_plot), loc = 0, scale = 1)
                # print(f"c2: {c2}")
                slog.debug(f"c2: {}".format(c2))
                t2 = poi_data[2] * math.exp(c2/len(param_to_plot))      #threshold value for 95% confidence
                # print(f"t2: {t2}")
                slog.debug("t2: {}".format(t2))
                ax[i].axhline(y = t2, color='green', linestyle='solid')   #plotting a horizontal line for SoS

                #setting the y-axis limit
                ax[i].set_ylim(min_val * 0.05, t2*1.2)

            #plot labeling and saving
            plt.suptitle("Profile Likelihood")
            fig.supylabel("Sum of Squares")
            ##############################################################
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
            slog.debug(e)
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

        slog.debug("page_name: {}".format(page_name))
        if page_name == 'main':
            model = self.copasi_model

            #HB removing the following block for pl task as we don't need variables to be plotted
            # try:
            #     variable_choices = model.get_variables(pretty=True)
            # except:
            #     raise

            # If the variables GET field hasn't been set, preset it to all variables
            try:
                assert request.GET.get('custom') == 'true'
                # form = PlotUpdateForm(request.GET, variable_choices=variable_choices)
                #above line is modified by HB for PL task as follows
                form = PlotUpdateForm(request.GET)

            except:
                # form = PlotUpdateForm(variable_choices=variable_choices,
                #                       initial={'variables': range(len(variable_choices))})
                #above line is modified by HB for PL task as follows
                form = PlotUpdateform(initial={'key':'value'})

            if form.is_valid():
                # variables = map(int, form.cleaned_data['variables']) #removed for pl task
                log = form.cleaned_data['logarithmic']
                legend = form.cleaned_data['legend']
                grid = form.cleaned_data['grid']
            else:
                # variables = range(len(variable_choices)) #removed for pl task
                log = False
                legend = True
                grid = True


            # construct the string to load the image file
            # img_string = '?variables=' + str(variables).strip('[').rstrip(']').replace(' ', '')
            #HB above line is commented out for PL task
            img_string = ''
            img_string += '&name=plot'
            if log:
                img_string += '&log=true'
            if stdev:
                img_string += '&stdev=true'
            if legend:
                img_string += '&legend=true'
            if grid:
                img_string += '&grid=true'

            output = {'form': form, 'img_string': img_string}

            return output

    def get_results_download_data(self, request):
        param_to_plot = self.copasi_model.process_original_pl_model()
        page_name = request.GET.get('name', 'main')
        slog.debug("page_name: {}".format(page_name))
        # if page_name == 'main':
        return get_pl_plot(request, param_to_plot)

class PlotUpdateform(forms.Form):

    legend = forms.BooleanField(label="Show figure legend", required=False, initial=True)
    grid = forms.BooleanField(label="Show grid", required=False, initial=True)
    logarithmic = forms.BooleanField(label="Logarithmic Scale", required = False)
