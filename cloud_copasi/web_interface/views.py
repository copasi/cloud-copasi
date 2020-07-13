from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import View, TemplateView, RedirectView

#from django.template import RequestContext
#from django.views.generic import TemplateView, RedirectView, View, FormView
#from django.views.generic.edit import FormMixin, ProcessFormView
#from django.views.generic.base import ContextMixin
#from django.utils.decorators import method_decorator
#from django.contrib.auth.decorators import login_required, permission_required
#from django.contrib.auth import authenticate, login, logout
#from django.contrib.auth.forms import AuthenticationForm
#from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
#from django.contrib.auth import logout
#from django import forms
#import sys
#from boto.exception import BotoServerError
#from cloud_copasi.web_interface.models import AWSAccessKey, CondorPool, Task, EC2Instance, ElasticIP
#from cloud_copasi.web_interface.aws import resource_management_tools
import logging
from cloud_copasi import settings

log = logging.getLogger(__name__)
# Create your views here.
#
# class DefaultView(TemplateView):
#     page_title=''
#

class DefaultView(TemplateView):
    page_title=''


    def get(self, request, *args, **kwargs):
        #log.debug('GET request [\"%s\"]' % request.path)
        return super(DefaultView, self).get(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):

        #Override the template name if it is requested from the url
        if kwargs.get('template_name', None):
            self.template_name = kwargs['template_name']
        if self.page_title:
            kwargs['page_title'] = self.page_title
        #Check for errors in request.session
        kwargs['debug'] = settings.DEBUG
        errors = request.session.pop('errors', None)
        if errors:
            kwargs['errors'] = errors

        if request.user.is_authenticated:
            if hasattr(self, 'template_name') and self.template_name != 'homeN.html':
                #Don't show on the home screen, regardless of logged in or not
                kwargs['show_status_bar']=True
        return super(DefaultView, self).dispatch(request, *args, **kwargs)

class HomeView(DefaultView):
    template_name = 'homeN.html'
    page_title = "Home"

class LandingView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return reverse_lazy('my_account')
        else:
            return reverse_lazy('homeN')

def index(request):
    my_mes ={'message' : 'Hello! I am coming from views.py'}
    return render(request, 'index.html',context=my_mes)
