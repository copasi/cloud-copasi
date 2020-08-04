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
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic.edit import FormMixin, ProcessFormView
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from web_interface.views import RestrictedView, DefaultView, RestrictedFormView

from web_interface.models import AWSAccessKey, Task, EC2Instance,\
    ElasticIP, EC2Pool, Profile
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
import sys
from django.contrib.auth.forms import PasswordChangeForm
from web_interface.aws import vpc_tools, aws_tools, ec2_tools
from web_interface import models, form_tools
from django.views.decorators.cache import never_cache
from boto.exception import EC2ResponseError, BotoServerError
import boto.exception
from web_interface.models import VPC, CondorPool
from django.forms.forms import NON_FIELD_ERRORS
import logging
from django.forms.utils import ErrorList
# from cloud_copasi.django_recaptcha.fields import ReCaptchaField
from web_interface.account import user_countries
from cloud_copasi import settings
from django.views.generic.base import ContextMixin
from web_interface.pools import condor_tools
import tempfile
import re
import os

log = logging.getLogger(__name__)

class MyAccountView(RestrictedView):
    template_name = 'account/account_homeN.html'
    page_title = 'My account'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        user = request.user

        return super(MyAccountView, self).dispatch(request, *args, **kwargs)

class KeysView(MyAccountView):
    """View to display keys
    """
    template_name = 'account/key_viewN.html'
    page_title = 'Keys'

class AddKeyForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(AddKeyForm, self).__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data['name']
        if AWSAccessKey.objects.filter(name=name,user=self.user).count() > 0:
            raise forms.ValidationError('A key with this name already exists')
        return name

    def clean_access_key_id(self):
        access_key_id = self.cleaned_data['access_key_id']
        if AWSAccessKey.objects.filter(access_key_id=access_key_id,user=self.user).count() > 0:
            raise forms.ValidationError('An access key with this ID already exists')
        return access_key_id



    name = forms.CharField(max_length=50, help_text='For your convenience, assign a unique name to this access key', )

    access_key_file = forms.FileField(help_text = 'The AWS keypair file, typically called rootkey.csv. Either upload this file, or enter the details manually below.',
                                      required=False)

    access_key_id = forms.CharField(max_length=20, min_length=20, required=False, label='Access key ID',
                                    help_text='The 20-character AWS access key ID. Only enter this if you do not upload a key file',
                                    )

    secret_key = forms.CharField(max_length=40, min_length=40, required=False, label='Secret access key',
                                 help_text='The 40-character secret access key associated with the access key ID. Only enter this if you do not upload a key file',
                                 )


class KeysAddView(RestrictedFormView):
    template_name = 'account/key_addN.html'
    page_title = 'Add key'
    success_url = reverse_lazy('my_account_keys')
    form_class = AddKeyForm


    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Adding key and setting up VPC'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page.'


        return super(KeysAddView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs =  super(RestrictedFormView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, *args, **kwargs):
        form=kwargs['form']
        #Create the key object and save it

        #Was a file uploaded? If so, first check if access_key_id and secret_key are blank
        if self.request.FILES.get('access_key_file'):
            if form.cleaned_data['access_key_id'] != '' or form.cleaned_data['secret_key'] != '':
                form._errors[NON_FIELD_ERRORS] = 'Either upload a file or enter the key details manually'
                return self.form_invalid(self, *args, **kwargs)

            #Try and save the key file to a temp file
            temp_file_descriptor, temp_filename = tempfile.mkstemp()
            form_tools.handle_uploaded_file(self.request.FILES['access_key_file'], temp_filename)

            access_key_re = re.compile(r'AWSAccessKeyId\=(?P<access_key>.{20})\n*')
            secret_key_re = re.compile(r'AWSSecretKey\=(?P<secret_key>.{40})\n*')

            access_key=''
            secret_key=''

            temp_file = open(temp_filename, 'r')
            total_read_lines = 5 #How many lines to read before giving up
            line_count = 0
            for line in temp_file.readlines():
                if access_key_re.match(line):
                    access_key = access_key_re.match(line).group('access_key')
                elif secret_key_re.match(line):
                    secret_key = secret_key_re.match(line).group('secret_key')
                if line_count < total_read_lines:
                    line_count +=1
                    #Count the numeber of lines. Should be in the first 2 lines anyway, so this gives a bit of leeway
                else:
                    break
            temp_file.close()
            os.remove(temp_filename)

            if not (access_key and secret_key):
                form._errors[NON_FIELD_ERRORS] = 'The uploaded access key could not be read'
                return self.form_invalid(self, *args, **kwargs)

            key = AWSAccessKey(access_key_id = access_key, secret_key=secret_key)
        else:
            if form.cleaned_data['access_key_id'] == '' or  form.cleaned_data['secret_key'] == '':
                form._errors[NON_FIELD_ERRORS] = 'Either upload a file or enter the key details manually'
                return self.form_invalid(self, *args, **kwargs)
            else:
                key = AWSAccessKey()
                key.access_key_id = form.cleaned_data['access_key_id']
                key.secret_key = form.cleaned_data['secret_key']

        key.user = self.request.user
        key.name = form.cleaned_data['name']
        key.save()
        try:
            #Authenticate the keypair
            vpc_connection, ec2_connection = aws_tools.create_connections(key)
            #Run a test API call
            ec2_connection.get_all_regions()

        except Exception as e:
            #Since we are about to return form_invalid, add the errors directly to the form non field error list
            #kwargs['errors']=aws_tools.process_errors([e])
            key.delete()
            error_list = [x[1] for x in e.errors]
            form._errors[NON_FIELD_ERRORS] = ErrorList(error_list)
            return self.form_invalid(self, *args, **kwargs)

        #And launch the VPC
        try:

            vpc = vpc_tools.create_vpc(key, vpc_connection, ec2_connection)

        except Exception as e:
            log.exception(e)
            try:
                vpc.delete()
            except:
                pass
            try:
                key.delete()
            except:
                pass
            form._errors[NON_FIELD_ERRORS] = 'Error launching VPC for key'
            return self.form_invalid(self, *args, **kwargs)
        return super(KeysAddView, self).form_valid(*args, **kwargs)


class ShareKeyForm(forms.Form):
    username = forms.CharField(max_length=30)


class KeysShareView(RestrictedFormView):
    form_class = ShareKeyForm
    template_name = 'account/key_share.html'
    page_title = 'Share key'
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        key = AWSAccessKey.objects.get(id=kwargs['key_id'])
        assert key.user == self.request.user
        assert key.copy_of == None


        if kwargs.get('remove'):
            unshare_from = User.objects.get(id=kwargs['user_id'])

            unshare_key = AWSAccessKey.objects.get(copy_of=key, user=unshare_from)
            unshare_key.delete()
            return HttpResponseRedirect(reverse_lazy('my_account_keys_share', kwargs={'key_id': kwargs['key_id']}))


        shared_keys = AWSAccessKey.objects.filter(copy_of=key)

        shared_users = [key.user for key in shared_keys]

        kwargs['shared_users'] = shared_users

        return super(KeysShareView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, *args, **kwargs):

        form = kwargs['form']
        self.success_url = reverse_lazy('my_account_keys_share', kwargs={'key_id':kwargs['key_id']})


        #Get the pool we want to share
        key = AWSAccessKey.objects.get(id=kwargs['key_id'])
        assert key.user == self.request.user
        assert key.copy_of == None



        #Lookup username to see if it is valid
        try:
            user = User.objects.get(username=form.cleaned_data['username'])
        except:
            form._errors[NON_FIELD_ERRORS] = ErrorList(['Username not recognized'])
            return self.form_invalid(*args, **kwargs)

        try:
            assert user != self.request.user
        except:
            form._errors[NON_FIELD_ERRORS] = ErrorList(['Sorry, you can\'t share a pool with yourself'])
            return self.form_invalid(*args, **kwargs)



        try:
            assert AWSAccessKey.objects.filter(copy_of__id=key.id, user=user).count() == 0
        except:
            form._errors[NON_FIELD_ERRORS] = ErrorList(['This key has already been shared with that user'])
            return self.form_invalid(*args, **kwargs)

        vpc = key.vpc

        copy_of = AWSAccessKey.objects.get(pk=key.pk)


        #Make a copy of the pool
        #pool.copy_of = pool
        key.pk = None
        key.id = None

        key.copy_of = copy_of
        key.user = user




        key.save()

        #And of the VPC
        vpc.pk = None
        vpc.id = None

        vpc.pk = None
        vpc.id = None
        vpc.access_key = key
        vpc.save()

        return super(KeysShareView, self).form_valid(*args, **kwargs)

class KeyRenameForm(forms.Form):
    new_name =forms.CharField(max_length=100)

class KeysRenameView(RestrictedFormView):
    page_title='Rename pool'
    template_name = 'account/key_rename.html'
    form_class = KeyRenameForm

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        key = AWSAccessKey.objects.get(id=kwargs['key_id'])
        assert key.user == request.user
        kwargs['key'] = key
        return super(KeysRenameView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, *args, **kwargs):

        form = kwargs['form']
        new_name = form.cleaned_data['new_name']
        key = AWSAccessKey.objects.get(id=kwargs['key_id'])
        assert key.user == self.request.user

        existing_keys = AWSAccessKey.objects.filter(user=self.request.user).filter(name=new_name)

        if existing_keys.count()>0:
            form._errors[NON_FIELD_ERRORS] = ErrorList(['A key with this name already exists'])
            return self.form_invalid(self, *args, **kwargs)

        key.name = new_name
        key.save()
        self.success_url = reverse_lazy('my_account_keys',)
        return super(KeysRenameView, self).form_valid(*args, **kwargs)




class PasswordChangeView(RestrictedFormView):
    template_name = 'account/password_changeN.html'
    page_title = 'Change password'
    form_class = PasswordChangeForm
    success_url = reverse_lazy('my_account')

    def get_form_kwargs(self):
        kwargs = super(PasswordChangeView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, *args, **kwargs):
        form=kwargs['form']
        form.save()
        return super(PasswordChangeView, self).form_valid(*args, **kwargs)

class KeysDeleteView(MyAccountView):
    template_name = 'account/key_delete_confirm.html'
    page_title = 'Confirm key delete'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):

        key_id = self.kwargs['key_id']
        key = AWSAccessKey.objects.get(id=key_id)
        kwargs['key'] = key
        assert key.user == request.user

        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Removing key and associated VPC'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page.'



        #Is this an original key or is it a copy
        if key.copy_of == None:
            original = True
        else:
            original = False

        if original:
            #Build a list of any pools and running jobs that will be terminated when this pool is terminated
            try:
                pools = EC2Pool.objects.filter(vpc__vpc_id = key.vpc.vpc_id)
            except:
                pools = []
            shared_keys = AWSAccessKey.objects.filter(copy_of=key)
            shared_user_ids = [shared_key.user.id for shared_key in shared_keys]
            kwargs['shared_users'] = User.objects.filter(id__in=shared_user_ids)



        else:
            #A copy of a key. If so, we'll not be deleting the real vpc, adn so
            try:
                pools = EC2Pool.objects.filter(vpc__id=key.vpc.id)
            except:
                pools = []

        kwargs['pools'] = pools
        errors=[]



        if kwargs['confirmed']:

            #Go through and terminate each of the running pools
            for pool in pools:
                #First, remove any running tasks
                running_tasks = pool.get_running_tasks()
                for task in running_tasks:
                    for subtask in task.subtask_set.all():
                        condor_tools.remove_task(subtask)
                    task.delete()

                other_tasks = Task.objects.filter(condor_pool=pool).exclude(pk__in=running_tasks)
                #Then 'prune' the remaining tasks to remove the pool as a foreignkey
                for task in other_tasks:
                    task.condor_pool = None
                    task.set_custom_field('condor_pool_name', pool.name)
                    task.save()


                ec2_tools.terminate_pool(pool)

            if original:
                #We also need to delete the vpc (and any associated)
                try:
                    related = AWSAccessKey.objects.filter(copy_of=key)
                    for related_key in related:
                        related_key.delete()

                    if key.vpc != None:
                        vpc_connection, ec2_connection = aws_tools.create_connections(key)

                        errors += (vpc_tools.delete_vpc(key.vpc, vpc_connection, ec2_connection))

                        if errors != []:
                            log.exception(errors)
                            request.session['errors'] = aws_tools.process_errors(errors)
                except Exception as e:
                    log.exception(e)
                #And delete the key
                key.delete()
            else:
                #Just delete the key object and the vpc
                key.delete()

            return HttpResponseRedirect(reverse_lazy('my_account_keys'))

        return super(KeysDeleteView, self).dispatch(request, *args, **kwargs)


class VPCConfigView(MyAccountView):
    template_name = 'account/vpc_configN.html'
    page_title ='VPC configuration'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        key_id = self.kwargs['key_id']
        try:
            key = AWSAccessKey.objects.get(id=key_id)
            assert key.user == request.user
        except Exception as e:
            request.session['errors'] = [e]
            return HttpResponseRedirect(reverse_lazy('my_account_keys'))
        kwargs['key'] = key

        assert key.copy_of == None
        return super(VPCConfigView,self).dispatch(request, *args, **kwargs)


class AccountRegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)

    email_address = forms.EmailField()

    institution = forms.CharField(max_length=50)
    country = forms.ChoiceField(choices=user_countries.COUNTRIES, initial='US')

    terms = forms.BooleanField(required=True,
                               label='Agree to terms and conditions?',
                               help_text = 'You must agree to the terms and conditions in order to register. Click <a href="%s" target="new">here</a> for further details',
                               )


   # captcha = ReCaptchaField(attrs={'theme': 'clean'}, label='Enter text')

    def __init__(self, *args, **kwargs):
        super(AccountRegisterForm, self).__init__(*args, **kwargs)
        self.fields['terms'].help_text = self.fields['terms'].help_text % reverse_lazy('help_terms')

    class Meta():
        model=User
        fields = ('username', 'email_address', 'first_name', 'last_name', 'institution', 'country', 'password1', 'password2', 'terms',)


class AccountRegisterView(FormView):
    page_title = 'Register'
    template_name = 'account/registerN.html'
    form_class = AccountRegisterForm
    success_url = reverse_lazy('my_account')


    def get_context_data(self, **kwargs):
        context = FormView.get_context_data(self, **kwargs)
        context['page_title'] = self.page_title
        context['allow_new_registrations'] = settings.ALLOW_NEW_REGISTRATIONS
        return context

    def dispatch(self, request, *args, **kwargs):

        #Only display if the user is not logged in
        if request.user.is_authenticated:
            return HttpResponseRedirect(self.success_url)

        return super(AccountRegisterView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form, *args, **kwargs):

        assert settings.ALLOW_NEW_REGISTRATIONS

        #Firstly, save and authenticate the user
        form.save()
        username = form.cleaned_data['username']
        password = form.cleaned_data['password2']

        user = authenticate(username=username, password=password)

        #And log in the user
        login(self.request, user)

        user.email = form.cleaned_data['email_address']
        profile = Profile(user=user, institution=form.cleaned_data['institution'])
        profile.save()
        user.save()

        return super(AccountRegisterView, self).form_valid(form, *args, **kwargs)

class AccountProfileForm(forms.Form):
    email_address = forms.EmailField(required=True)
    institution = forms.CharField(required = True, max_length=50)
    send_pool_emails = forms.BooleanField(required=False,
                                          label='Send EC2 pool emails',
                                          help_text = 'Send emails relating to EC2 pool activity, e.g. when a pool has been automatically terminated.',
                                          )
    send_task_emails = forms.BooleanField(required=False,
                                          label='Send task emails',
                                          help_text = 'Send emails relating to task activity, e.g. when a task has completed or encountered an error.')

class AccountResetPasswordView(FormView):
    page_tile = 'Reset password'
    template_name = 'account/reset_password.html'

        #Add the page title to the top of the page
    def get_context_data(self, **kwargs):
        context = FormView.get_context_data(self, **kwargs)
        context['page_title'] = self.page_title
        return context

class AccountProfileForm(forms.Form):
    email_address = forms.EmailField(required=True)
    institution = forms.CharField(required = True, max_length=50)
    send_pool_emails = forms.BooleanField(required=False,
                                          label='Send EC2 pool emails',
                                          help_text = 'Send emails relating to EC2 pool activity, e.g. when a pool has been automatically terminated.',
                                          )
    send_task_emails = forms.BooleanField(required=False,
                                          label='Send task emails',
                                          help_text = 'Send emails relating to task activity, e.g. when a task has completed or encountered an error.')



class AccountProfileView(RestrictedFormView):
    page_title = 'Account profile options'
    template_name = 'account/profileN.html'
    success_url = reverse_lazy('my_account')
    form_class = AccountProfileForm

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not hasattr(user, 'profile'):
            profile = Profile(user = user, institution = '')
            profile.save()
        else:
            profile = user.profile

        self.initial['email_address'] = user.email
        self.initial['institution'] = profile.institution
        self.initial['send_pool_emails'] = profile.pool_emails
        self.initial['send_task_emails'] = profile.task_emails

        return super(AccountProfileView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, *args, **kwargs):

        assert hasattr(self.request.user, 'profile')
        form = kwargs['form']
        user = self.request.user
        user.email = form.cleaned_data['email_address']
        user.profile.institution = form.cleaned_data['institution']
        user.profile.pool_emails = form.cleaned_data['send_pool_emails']
        user.profile.task_emails = form.cleaned_data['send_task_emails']

        user.profile.save()
        user.save()

        return super(AccountProfileView, self).form_valid(*args, **kwargs)
