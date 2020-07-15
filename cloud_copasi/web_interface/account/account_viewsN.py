#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
# from django.http import HttpResponse, HttpResponseForbidden, HttpResponseServerError
from django.views.generic import TemplateView, RedirectView, View, FormView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
# from django.views.generic.edit import FormMixin, ProcessFormView
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from web_interface.views import RestrictedView, DefaultView, RestrictedFormView

from web_interface.models import AWSAccessKey, Task, EC2Instance,\
    ElasticIP, EC2Pool, Profile
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
# import sys
# from django.contrib.auth.forms import PasswordChangeForm
from web_interface.aws import vpc_tools, aws_tools, ec2_tools
from web_interface import models, form_tools
# from django.views.decorators.cache import never_cache
# from boto.exception import EC2ResponseError, BotoServerError
# import boto.exception
from web_interface.models import VPC, CondorPool
# from django.forms.forms import NON_FIELD_ERRORS
import logging
# from django.forms.utils import ErrorList
# from cloud_copasi.django_recaptcha.fields import ReCaptchaField
from web_interface.account import user_countries
from cloud_copasi import settings
# from django.views.generic.base import ContextMixin
# from cloud_copasi.web_interface.pools import condor_tools
# import tempfile
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



class AccountRegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)

    email_address = forms.EmailField()

    institution = forms.CharField(max_length=50)
    country = forms.ChoiceField(choices=user_countries.COUNTRIES, initial='US')

    terms = forms.BooleanField(required=True,
                               label='Agree to terms and conditions?',
                               help_text = 'You must agree to the terms and conditions in order to register. \
                               Click <a href="%s" target="new">here</a> for further details',
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
            return HttpResponseRedirect(reverse_lazy('my_account'))

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
