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
from django.core.urlresolvers import reverse_lazy
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from cloud_copasi.web_interface.views import RestrictedView, DefaultView, RestrictedFormView
from cloud_copasi.web_interface.models import AWSAccessKey, Task, EC2Instance,\
    ElasticIP, EC2Pool
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
import sys
from django.contrib.auth.forms import PasswordChangeForm
from cloud_copasi.web_interface.aws import vpc_tools, aws_tools
from cloud_copasi.web_interface import models
from django.views.decorators.cache import never_cache
from boto.exception import EC2ResponseError, BotoServerError
import boto.exception
from cloud_copasi.web_interface.models import VPC, CondorPool
from django.forms.forms import NON_FIELD_ERRORS
import logging
from django.forms.util import ErrorList
from cloud_copasi.django_recaptcha.fields import ReCaptchaField
from cloud_copasi.web_interface.account import user_countries
from cloud_copasi import settings
from django.views.generic.base import ContextMixin

log = logging.getLogger(__name__)



class MyAccountView(RestrictedView):
    template_name = 'account/account_home.html'
    page_title = 'My account'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        
        user = request.user
       
        kwargs['compute_nodes'] = EC2Instance.objects.filter(ec2_pool__vpc__access_key__user=user)
        kwargs['elastic_ips'] = ElasticIP.objects.filter(vpc__access_key__user=user)
        
        
        
        kwargs['access_keys'] = AWSAccessKey.objects.filter(user=user)
        kwargs['compute_pools'] = EC2Pool.objects.filter(vpc__access_key__user=user)
        
        tasks = Task.objects.filter(condor_pool__user = user)
        kwargs['running_tasks'] = tasks.filter(status='new')|tasks.filter(status='running')|tasks.filter(status='transfer')
        kwargs['finished_tasks'] =  tasks.filter(status='finished')
        kwargs['task_errors'] =  tasks.filter(status='error')
        
        return super(MyAccountView, self).dispatch(request, *args, **kwargs)
    

class KeysView(RestrictedView):
    """View to display keys
    """
    template_name = 'account/key_view.html'
    page_title = 'Keys'

class AddKeyForm(forms.ModelForm):
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

    class Meta:
        model = AWSAccessKey
        fields = ('name', 'access_key_id', 'secret_key')
        widgets = {
            'access_key_id' : forms.TextInput(attrs={'style':'width:20em'}),
            'secret_key' : forms.TextInput(attrs={'style':'width:40em'}),
            }


class KeysAddView(RestrictedFormView):
    template_name = 'account/key_add.html'
    page_title = 'Add key'
    success_url = reverse_lazy('my_account_keys')
    form_class = AddKeyForm
    
    def get_form_kwargs(self):
        kwargs =  super(RestrictedFormView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, *args, **kwargs):
        form=kwargs['form']
        #Create the key object and save it
        key = form.save(commit=False)
        key.user = self.request.user
        key.save()
        try:
            #Authenticate the keypair
            vpc_connection, ec2_connection = aws_tools.create_connections(key)
            #Run a test API call
            ec2_connection.get_all_regions()
            
        except Exception, e:
            #Since we are about to return form_invalid, add the errors directly to the form non field error list
            #kwargs['errors']=aws_tools.process_errors([e])
            key.delete()
            error_list = [x[1] for x in e.errors]
            form._errors[NON_FIELD_ERRORS] = ErrorList(error_list)
            return self.form_invalid(self, *args, **kwargs)
           
        return super(KeysAddView, self).form_valid(*args, **kwargs)

class PasswordChangeView(RestrictedFormView):
    template_name = 'account/password_change.html'
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
        try:
            key_id = self.kwargs['key_id']
            key = AWSAccessKey.objects.get(id=key_id)
            kwargs['key'] = key
            assert key.user == request.user
        except:
            return HttpResponseServerError()
        
        vpcs = VPC.objects.filter(access_key=key)
        if vpcs.count() > 0:
            error_title = 'VPC still associated'
            error_message = 'A VPC is still associated with this access key. You must remove the VPC before the access key can be deleted.'
            request.session['errors'] = [(error_title, error_message)]
            return HttpResponseRedirect(reverse_lazy('vpc_config', kwargs={'key_id':key.id}))
        
        if self.kwargs['confirmed']:
            try:
                key.delete()
                return HttpResponseRedirect(reverse_lazy('my_account_keys'))
            except:
                raise
        else:
            return MyAccountView.dispatch(self, request, *args, **kwargs)
        
class VPCStatusView(MyAccountView):
    template_name='account/vpc_status.html'
    page_title='VPC status'
    

class VPCConfigView(MyAccountView):
    template_name = 'account/vpc_config.html'
    page_title ='VPC configuration'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        key_id = self.kwargs['key_id']
        try:
            key = AWSAccessKey.objects.get(id=key_id)
            assert key.user == request.user
        except Exception, e:
            request.session['errors'] = [e]
            return HttpResponseRedirect(reverse_lazy('vpc_status'))
        kwargs['key'] = key
        
        return super(VPCConfigView,self).dispatch(request, *args, **kwargs)


class VPCAddView(RedirectView):
    
    def get_redirect_url(self, **kwargs):
        key_id=kwargs['key_id']
        return reverse_lazy('vpc_config', kwargs={'key_id':key_id})
    
    permanent=False
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        key_id = self.kwargs['key_id']
        try:
            key = AWSAccessKey.objects.get(id=key_id)
            assert key.user == request.user
        except Exception, e:
            request.session['errors'] =[e]
            return super(VPCAddView, self).dispatch(request, *args, **kwargs)
        kwargs['key'] = key
        
        #Create a VPC associated with the key
        try:
            vpc_connection, ec2_connection = aws_tools.create_connections(key)
            
            vpc_tools.create_vpc(key, vpc_connection, ec2_connection)
            
            vpc_connection.close()
            ec2_connection.close()
        except Exception, e:
            request.session['errors'] = aws_tools.process_errors([e])
        
        return super(VPCAddView, self).dispatch(request, *args, **kwargs)

class VPCRemoveView(RedirectView):
    
    def get_redirect_url(self, **kwargs):
        key_id=kwargs['key_id']
        return reverse_lazy('vpc_config', kwargs={'key_id':key_id})
    
    permanent=False
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        key_id = self.kwargs['key_id']
        key = AWSAccessKey.objects.get(id=key_id)
        vpc = key.vpc
        assert key.user == request.user
        kwargs['key'] = key
        
        #Make sure there are no pools running on the vpc
        pools = CondorPool.objects.filter(vpc=vpc)
        if pools.count() > 0:
            error_title='Compute pools still running'
            error_message='One or more compute pools are still running on this VPC. These must be terminated before the VPC can be removed.'
            request.session['errors'] = [(error_title, error_message)]
            return HttpResponseRedirect(reverse_lazy('pool_list'))
        #Create a VPC associated with the key
        errors=[]
        try:
            vpc_connection, ec2_connection = aws_tools.create_connections(key)
            
            errors.append(vpc_tools.delete_vpc(vpc, vpc_connection, ec2_connection))

        except Exception, e:
            errors.append(e)
        
        if errors != []:
            request.session['errors'] = aws_tools.process_errors(errors)
            
        
        return super(VPCRemoveView, self).dispatch(request, *args, **kwargs)


class AccountRegisterForm(UserCreationForm):
    
    
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)

    email_address = forms.EmailField()

    institution = forms.CharField(max_length=50)
    country = forms.ChoiceField(choices=user_countries.COUNTRIES, initial='GB')
    
    terms = forms.BooleanField(required=True, label='Agree to terms and conditions?',
                               help_text = 'You must agree to the terms and conditions in order to register. Click <a href="%s" target="new">here</a> for further details')
    
    
    captcha = ReCaptchaField(attrs={'theme': 'clean'}, label='Enter text')
    
    def __init__(self, *args, **kwargs):
        super(AccountRegisterForm, self).__init__(*args, **kwargs)
        self.fields['terms'].help_text = self.fields['terms'].help_text % reverse_lazy('terms')
    
    class Meta:
        model=User
        fields = ('username', 'email_address', 'first_name', 'last_name', 'institution', 'country', )

class AccountRegisterView(FormView):
    page_title = 'Register'
    template_name = 'account/register.html'
    form_class = AccountRegisterForm
    success_url = reverse_lazy('my_account')
    
    
    def get_context_data(self, **kwargs):
        context = FormView.get_context_data(self, **kwargs)
        context['page_title'] = self.page_title
        context['allow_new_registrations'] = settings.ALLOW_NEW_REGISTRATIONS
        return context

    def dispatch(self, request, *args, **kwargs):
        
        #Only display if the user is not logged in
        if request.user.is_authenticated():
            return HttpResponseRedirect(reverse_lazy('my_account'))
        

        
        return super(AccountRegisterView, self).dispatch(request, *args, **kwargs)
    
    def form_valid(self, form, *args, **kwargs):
        
        assert settings.ALLOW_NEW_REGISTRATIONS
        
        #Firstly, save and authenticate the user
        form.save()
        username = form.cleaned_data['username']
        password = form.cleaned_data['password2']
        
        user = authenticate(username=username,
                            password=password)
        
        #And log in the user
        login(self.request, user)
        
        return super(AccountRegisterView, self).form_valid(form, *args, **kwargs)
        
    
class AccountResetPasswordView(FormView):
    page_tile = 'Reset password'
    template_name = 'account/reset_password.html'
    
        #Add the page title to the top of the page
    def get_context_data(self, **kwargs):
        context = FormView.get_context_data(self, **kwargs)
        context['page_title'] = self.page_title
        return context


    