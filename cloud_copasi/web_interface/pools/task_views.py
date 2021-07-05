#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseServerError
from django.views.generic import TemplateView, RedirectView, View, FormView
from django.views.generic.edit import FormMixin, ProcessFormView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django import forms
from cloud_copasi.web_interface.views import RestrictedView, DefaultView, RestrictedFormView
from cloud_copasi.web_interface.models import AWSAccessKey, VPC, CondorPool, CondorJob, Task, Subtask
from cloud_copasi.web_interface import models, aws
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
import sys
from cloud_copasi.web_interface.account.account_viewsN import MyAccountView
from django.contrib.auth.forms import PasswordChangeForm
from boto.vpc import VPCConnection
from boto.ec2 import EC2Connection
from cloud_copasi.web_interface.aws import vpc_tools, ec2_tools
#import task_tools, condor_tools
from cloud_copasi.web_interface.pools import task_tools, condor_tools
from cloud_copasi.web_interface import form_tools
import tempfile, os
from cloud_copasi import settings, copasi
# from . import copasi
from cloud_copasi.copasi.model import CopasiModel
from cloud_copasi.web_interface import task_plugins
from cloud_copasi.web_interface.task_plugins import base, tools, plugins
from django.forms.forms import NON_FIELD_ERRORS
import logging
from datetime import timedelta
from django.utils.datetime_safe import datetime
import shutil
from django.core.files.uploadedfile import TemporaryUploadedFile, UploadedFile
import zipfile
import json


log = logging.getLogger(__name__)
########### following lines are set by HB for debugging
logging.basicConfig(
        filename='/home/cloudcopasi/log/debug.log',
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%m/%d/%y %I:%M:%S %p',
        level=logging.DEBUG
    )
check = logging.getLogger(__name__)
######################################################

class NewTaskView(RestrictedFormView):
    template_name = 'tasks/task_newN.html'
    page_title = 'New task'

    def __init__(self, *args, **kwargs):
        self.form_class = base.BaseTaskForm
        check.debug("reached in __init_ in task_views.py **********")#added by HB
        return super(NewTaskView, self).__init__(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(NewTaskView, self).get_form_kwargs()
        kwargs['user']=self.request.user
        kwargs['task_types'] = tools.get_task_types()
        check.debug("reached in get_from_kwargs in task_views.py **********")#added by HB
        return kwargs

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        #If task_type has been set, change the form class
        task_type = request.POST.get('task_type')
       
        #added by HB
        check.debug("@@ (in task_views.py) @@ task_type:")
        check.debug(task_type)
        if task_type:
            task_form = tools.get_form_class(task_type)
            self.form_class = task_form


        #Ensure we have at least 1 running condor pool
        pools = CondorPool.objects.filter(user=request.user)
        if pools.count() == 0:
            request.session['errors']=[('No running compute pools', 'You must have configured at least 1 compute pool before you can submit a task')]
            return HttpResponseRedirect(reverse_lazy('pool_list'))

        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Submitting task'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. Submitting a task can take several minutes'

        check.debug("Dispatch function is finishing....") ##added by HB
        return super(NewTaskView,self).dispatch(request, *args, **kwargs)

    def form_valid(self, form,  *args, **kwargs):

        #Check we are authorized to run on this pool
        compute_pool = form.cleaned_data['compute_pool']
        request = self.request

        assert isinstance(compute_pool, CondorPool)
        assert compute_pool.user == request.user

        check.debug('Submitting task to compute pool %s (%s)' % (compute_pool.name, compute_pool.get_pool_type()))

        ########################################################################
        #Process the uploaded copasi file (and other files?)
        ########################################################################

        #Handle uploaded files...
        #Ensure the directory we're adding the file to exists
        if not os.path.exists(settings.STORAGE_DIR):
            os.mkdir(settings.STORAGE_DIR)

        #And the directory for the user
        #Takes the form userid.username
        user_dir = '%d.%s' % (request.user.id, request.user.username)
        user_dir_path = os.path.join(settings.STORAGE_DIR, user_dir)
        if not os.path.exists(user_dir_path):
            os.mkdir(user_dir_path)


        task = Task()
        task.name = form.cleaned_data['name']
        task.condor_pool = form.cleaned_data['compute_pool']
        task.user = request.user
        task.task_type = form.cleaned_data['task_type']

        task.original_model = 'original_model.cps'

        
        check.debug("@@(in task_views.py)@@ task.name:") #added by HB
        check.debug(task.name)
        check.debug("@@(in task_views.py)@@ task.user:") #added by HB
        check.debug(task.user)
        check.debug("@@(in task_views.py)@@ task.task_type:") #added by HB
        check.debug(task.task_type)
        check.debug("@@(in task_views.py)@@ task.original_model:") #added by HB
        check.debug(task.original_model)

        #Get a list of all fields that are only in the task form, and not in the base


        extra_fields = []
        base_form = base.BaseTaskForm
       
        for field_name in form.fields:
            if field_name not in base_form.base_fields:
                extra_fields.append((field_name, form.fields[field_name]))

        check.debug("@@(in task_views.py)@@ extra_fields:") #added by HB
        check.debug(extra_fields)


        #We have not yet created the directory to hold the files
        directory_created = False
        task.save() # Save the task so we can get a valid id

        #Save the custom task fields
        for field_name, field_object in extra_fields:
            #TODO: Is the file a zip file? Try unzipping it...
            if isinstance(field_object, forms.FileField) and isinstance(form.cleaned_data[field_name], UploadedFile):
                try:
                    #Create a directory to store the files for the task
                    #This will just be the id of the task
                    task_dir = str(task.id)
                    task_dir_path = os.path.join(user_dir_path, task_dir)

                    if os.path.exists(task_dir_path):
                        os.rename(task_dir_path, task_dir_path + '.old.' + str(datetime.now()))

                    os.mkdir(task_dir_path)
                    directory_created = True

                    data_file = request.FILES[field_name]
                    filename = data_file.name
                    data_destination = os.path.join(task_dir_path, filename)
                    form_tools.handle_uploaded_file(data_file, data_destination)

                    #Next, attempt to extract the file
                    #If this fails, assume the file is an ASCII data file, not a zip file
                    try:
                        data_files_list=[]
                        z = zipfile.ZipFile(data_destination)
                        #Record the name of each file in the zipfile

                        for name in  z.namelist():
                            data_files_list.append(name)

                        z.extractall(task_dir_path)
                    except zipfile.BadZipfile:
                        data_files_list=[]
                        #Assume instead that, if not a zip file, the file must be a data file, so leave it be.
                        #Write the name of the data file to data_files_list
                        data_files_list.append(filename)
                    task.set_custom_field('data_files', data_files_list)
                except Exception as e:
                    log.exception(e)
                    error_messages = ['An error occured while preparing the task data files',
                                       str(e),]
                    form._errors[NON_FIELD_ERRORS] = forms.forms.ErrorList(error_messages)
                    try:
                        shutil.rmtree(task.directory)
                    except:
                        pass
                    try:
                        task.delete()
                    except:
                        pass
                    kwargs['form']=form
                    return self.form_invalid(self, *args, **kwargs)

            else:
                task.set_custom_field(field_name, form.cleaned_data[field_name])



        task.save()

        try:
            if not directory_created:
                #Create a directory to store the files for the task
                #This will just be the id of the task
                task_dir = str(task.id)
                task_dir_path = os.path.join(user_dir_path, task_dir)

                if os.path.exists(task_dir_path):
                    os.rename(task_dir_path, task_dir_path + '.old.' + str(datetime.now()))

                os.mkdir(task_dir_path)

            task.directory = task_dir_path
            task.save()
                    #Next we need to create the directory to store the files for the task

            #working_dir = tempfile.mkdtemp(dir=settings.STORAGE_DIR)
            model_file = request.FILES['model_file']

            full_filename = os.path.join(task_dir_path, task.original_model)

            form_tools.handle_uploaded_file(model_file, full_filename)



            TaskClass = tools.get_task_class(form.cleaned_data['task_type'])
            check.debug("@@(in task_views.py)@@ TaskClass:") #added by HB
            check.debug(TaskClass) #added by HB

            task_instance = TaskClass(task)
        except Exception as e:
            log.exception(e)
            error_messages = ['An error occured while preparing the task model file',
                               str(e),]
            form._errors[NON_FIELD_ERRORS] = forms.forms.ErrorList(error_messages)
            try:
                shutil.rmtree(task.directory)
            except:
                pass
            try:
                task.delete()
            except:
                pass
            kwargs['form']=form
            return self.form_invalid(self, *args, **kwargs)

        #Validate the task
        valid = task_instance.validate()
        if valid != True:
            #valid message contained in valid hopefully.
            error_messages = ['Model file is not valid for the current task type',
                               str(valid),
                               ]
            form._errors[NON_FIELD_ERRORS] = forms.forms.ErrorList(error_messages)
            shutil.rmtree(task.directory)
            task.delete()
            kwargs['form'] = form


            return self.form_invalid(self, *args, **kwargs)

        try:
            task_instance.initialize_subtasks()

            subtask = task_instance.prepare_subtask(1)
            check.debug("@@(in task_views.py)@@ subtask:") #added by HB
            check.debug(subtask)

            condor_tools.submit_task(subtask)

            task.status = 'running'
            task.save()
        except Exception as e:
            log.exception(e)
            error_messages = ['An error occured while preparing the subtask',
                               str(e),]
            form._errors[NON_FIELD_ERRORS] = forms.forms.ErrorList(error_messages)
            try:
                shutil.rmtree(task.directory)
            except:
                pass
            try:
                task.delete()
            except:
                pass
            kwargs['form']=form
            return self.form_invalid(self, *args, **kwargs)

        #added by HB
        check.debug("@@ (in task_views.py) @@ finishing NewTaskView class") 
        return HttpResponseRedirect(reverse_lazy('task_details', kwargs={'task_id':task.id}))

class TaskListView(RestrictedView):

    template_name = 'tasks/task_listN.html'
    page_title = '...tasks'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        #Get a list of running tasks for this user
        user_tasks = Task.objects.filter(user=request.user)

        if kwargs['status'] == 'running':
            tasks = user_tasks.filter(status='new') | user_tasks.filter(status='running')

            tasks = tasks.order_by('-submit_time')

            self.page_title = 'Running tasks'
            kwargs['byline'] = 'Tasks that are queued or running'
        elif kwargs['status'] == 'finished':
            tasks = user_tasks.filter(status='finished').order_by('-finish_time')
            self.page_title = 'Finished tasks'
            kwargs['byline'] = 'Tasks that have finished running'
            kwargs['show_finish_time'] = True

        elif kwargs['status'] == 'error':
            tasks = user_tasks.filter(status='error').order_by('-submit_time')
            self.page_title = 'Task errors'
            kwargs['byline'] = 'Tasks that encountered an error while running'


        kwargs['tasks'] = tasks

        return super(TaskListView, self).dispatch(request, *args, **kwargs)

class TaskDetailsView(RestrictedView):

    template_name = 'tasks/task_detailsN.html'
    page_title = 'Task status'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        task_id = kwargs.pop('task_id')
        task = Task.objects.get(id=task_id)
        assert task.user == request.user

        task_custom_fields = json.loads(task.custom_fields)

        kwargs['task'] = task
        kwargs['task_display_type'] = task_plugins.tools.get_task_display_name(task.task_type)
        kwargs['config_options'] = task_custom_fields

        if task.status == 'finished':

            try:
                wall_clock_time = task.finish_time - task.submit_time
                wall_clock_time = timedelta(seconds=round(wall_clock_time.total_seconds()))
            except Exception as e:
                wall_clock_time = ''
            total_cpu = task.get_run_time()
            try:
                speed_up_factor = (total_cpu * 86400) / wall_clock_time.total_seconds()
                speed_up_factor = '%0.2f' % speed_up_factor
            except Exception as e:
                speed_up_factor = ''
            kwargs['speed_up_factor'] = speed_up_factor
            kwargs['wall_clock_time'] = wall_clock_time

        if task.status == 'error':
            #Try and determine the cause of the error
            kwargs['was_submitted'] = (CondorJob.objects.filter(subtask__task=task).count() > 0)
            kwargs['error_message'] = task.get_custom_field('error')
        return super(TaskDetailsView, self).dispatch(request, *args, **kwargs)

class SubtaskDetailsView(RestrictedView):

    template_name = 'tasks/subtask_detailsN.html'
    page_title = 'Subtask details'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        subtask_id = kwargs.pop('subtask_id')
        subtask = Subtask.objects.get(id=subtask_id)
        assert subtask.task.user == request.user

        kwargs['subtask'] = subtask

        kwargs['running_count'] = subtask.condorjob_set.filter(status='R').count()
        kwargs['finished_count'] = subtask.condorjob_set.filter(status='F').count()
        kwargs['idle_count'] = subtask.condorjob_set.filter(status='I').count()
        kwargs['held_count'] = subtask.condorjob_set.filter(status='H').count()


        return super(SubtaskDetailsView, self).dispatch(request, *args, **kwargs)

class TaskDeleteView(RestrictedView):

    template_name = 'tasks/task_deleteN.html'
    page_title = 'Delete task'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        task = Task.objects.get(id=kwargs['task_id'])
        assert task.user == request.user

        confirmed = kwargs['confirmed']

        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Deleting Task'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. Deleting a task can take several minutes'

        if not confirmed:
            kwargs['task']=task
            return super(TaskDeleteView, self).dispatch(request, *args, **kwargs)

        else:
            for subtask in task.subtask_set.all():
                try:
                    condor_tools.remove_task(subtask)
                except:
                    pass
            task.delete()


            return HttpResponseRedirect(reverse_lazy('running_task_list'))


class TaskResultView(RestrictedView):
    page_title = 'Results'
    template_name = 'tasks/result_viewN.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        task = Task.objects.get(id=kwargs['task_id'])
        assert task.user == request.user

        task_instance = task_plugins.tools.get_task_class(task.task_type)(task)

        kwargs['results'] = task_instance.get_results_view_data(request)
        kwargs['results_view_template_name'] = task_instance.get_results_view_template_name(request)
        kwargs['task'] = task
        kwargs['download_url'] = reverse_lazy('task_results_download', kwargs={'task_id':task.id})

        #If the results object has a form, put it in the top level context data namespace
        if kwargs['results'].get('form'):
            kwargs['form'] = kwargs['results'].get('form')

        return super(TaskResultView, self).dispatch(request, *args, **kwargs)

class TaskResultDownloadView(RestrictedView):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        task = Task.objects.get(id=kwargs['task_id'])
        assert task.user == request.user

        task_instance = task_plugins.tools.get_task_class(task.task_type)(task)

        return task_instance.get_results_download_data(request)

class TaskDirectoryDownloadView(RestrictedView):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        """Generate a tar.bz2 file of the results directory, and return it
        """
        try:
            task = Task.objects.get(id=kwargs['task_id'], user=request.user)
        except Exception as e:
            request.session['errors'] = [('Error Finding Job', 'The requested job could not be found')]
            log.exception(e)
            return HttpResponseRedirect(reverse_lazy('task_details'), kwargs={'task_id': kwargs['task_id']})

        filename = task_tools.zip_up_task(task)
        
        check.debug("@$@$@ filename in task_views.py: %s" %filename)

        #result_file = open(filename, 'r')
        #the above line is modified by HB as follows
        result_file = open(filename, 'r', encoding="utf-8")
        check.debug("@$@$@ result_file: %s" %result_file) #added by HB

        response = HttpResponse(result_file, content_type='application/x-bzip2')
        #above line is modified by HB  as follows
        #response = HttpResponse(result_file, content_type='application/zip')

        response['Content-Disposition'] = 'attachment; filename=' + task.name.replace(' ', '_') + '.tar.bz2'
        #above line is modified by HB as follows
        #response['Content-Disposition'] = 'attachment; filename=' + task.name.replace(' ', '_') + '.zip'
        response['Content-Length'] = os.path.getsize(filename)

        return response
