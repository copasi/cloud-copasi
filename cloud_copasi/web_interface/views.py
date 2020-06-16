from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import View, TemplateView

#from django.template import RequestContext
#from django.views.generic import TemplateView, RedirectView, View, FormView
#from django.views.generic.edit import FormMixin, ProcessFormView
#from django.views.generic.base import ContextMixin
#from django.utils.decorators import method_decorator
#from django.contrib.auth.decorators import login_required, permission_required
#from django.contrib.auth import authenticate, login, logout
#from django.contrib.auth.forms import AuthenticationForm
#from django.http import HttpResponseRedirect
#from django.urls import reverse_lazy
#from django.contrib.auth import logout
#from django import forms
#import sys
#from boto.exception import BotoServerError
#from cloud_copasi.web_interface.models import AWSAccessKey, CondorPool, Task, EC2Instance, ElasticIP
#from cloud_copasi.web_interface.aws import resource_management_tools
#import logging
#from cloud_copasi import settings

#log = logging.getLogger(__name__)
# Create your views here.
#
# class DefaultView(TemplateView):
#     page_title=''
#
# class HomeView(DefaultView):
#     template_name = 'home.html'
#     page_title = 'Home'

class HomeView(TemplateView):
    template_name = 'home.html'
    page_title = 'Home'

def index(request):
    my_mes ={'message' : 'Hello! I am coming from views.py'}
    return render(request, 'index.html',context=my_mes)
