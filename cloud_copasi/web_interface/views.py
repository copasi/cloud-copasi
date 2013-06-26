#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
# Create your views here.

from django.http import HttpResponse
from django.template import RequestContext
from django.views.generic import TemplateView, RedirectView, View, FormView
from django.views.generic.edit import FormMixin, ProcessFormView
from django.views.generic.base import ContextMixin
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth import logout
from django import forms
import sys
from boto.exception import BotoServerError
from cloud_copasi.web_interface.models import AWSAccessKey
from cloud_copasi.web_interface.aws import resource_management_tools
import logging
#Remember - class based views are not thread safe! Don't pass lists, dicts etc as args

log = logging.getLogger(__name__)

class DefaultView(TemplateView):
    page_title=''
    
    def get(self, request, *args, **kwargs):
        log.debug('GET request [\"%s\"]' % request.path)
        return super(DefaultView, self).get(request, *args, **kwargs)
    
    def dispatch(self, request, *args, **kwargs):
        kwargs['page_title'] = self.page_title
        #Check for errors in request.session
        errors = request.session.pop('errors', None)
        if errors:
            kwargs['errors'] = errors
        
        return super(DefaultView, self).dispatch(request, *args, **kwargs)


class RestrictedView(DefaultView):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        #Populate the context with information about the access keys
        user = request.user
        access_keys = AWSAccessKey.objects.filter(user=user)
        kwargs['access_keys'] = access_keys
        
        #resource_overview=resource_management_tools.get_unrecognized_resources(request.user)
        #Generate warnings
        #if not resource_overview.is_empty():
        #    log.debug('Unrecognized resources for user %s'%request.user)
        #kwargs['show_warning_bar']= not resource_overview.is_empty()
        #kwargs['resource_overview']=resource_overview
        
        return super(RestrictedView, self).dispatch(request, *args, **kwargs)

class RestrictedFormView(RestrictedView, FormMixin, ProcessFormView):
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        kwargs['form'] = self.get_form(self.get_form_class())
        
        return super(RestrictedFormView, self).dispatch(request, *args,**kwargs)
            
    def form_valid(self, *args, **kwargs):
        """
        If the form is valid, redirect to the supplied URL.
        """        
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, *args, **kwargs):
        """
        If the form is invalid, re-render the context data with the
        data-filled form and errors.
        """        
        return self.render_to_response(self.get_context_data(**kwargs))
    
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """              
        return self.render_to_response(self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form=kwargs['form']
        if form.is_valid():
            return self.form_valid(**kwargs)
        else:
            return self.form_invalid(**kwargs)

class LandingView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            return reverse_lazy('my_account')
        else:
            return reverse_lazy('home')
        

class HomeView(DefaultView):
    template_name='home.html'
    page_title = 'Home'
    

class AboutView(DefaultView):
    template_name = 'about/about_page.html'
    page_title = 'About'



class LogoutView(RedirectView):
    url = reverse_lazy('home')
    def dispatch(self, request, *args, **kwargs):
        logout(request)
        return super(LogoutView, self).dispatch(request, *args, **kwargs)
        
class LoginView(FormView):
    page_title = 'Sign in'
    success_url = reverse_lazy('landing_view')
    template_name = 'account/sign_in.html'
    form_class = AuthenticationForm
    initial={}
    
    def get_success_url(self):
        next_page = self.request.REQUEST.get('next', '')
        if next_page:
            return next_page
        else: 
            return FormView.get_success_url(self)
    
    def get_context_data(self, **kwargs):
        context = FormView.get_context_data(self, **kwargs)
        context['page_title'] = self.page_title
        return context
    
    def form_valid(self, form):
        login(self.request, form.get_user())
        return super(FormView,self).form_valid(form)
