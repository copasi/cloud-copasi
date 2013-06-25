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
from cloud_copasi.web_interface.views import RestrictedView, DefaultView, RestrictedFormView
from cloud_copasi.web_interface.models import AWSAccessKey, VPCConnection, CondorPool, EC2Instance
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
import sys
from django.contrib.auth.forms import PasswordChangeForm
from cloud_copasi.web_interface.aws import vpc_tools, aws_tools, ec2_tools,\
    resource_management_tools
from cloud_copasi.web_interface import models
from boto.exception import EC2ResponseError, BotoServerError
from cloud_copasi.web_interface.models import VPC
import logging

log = logging.getLogger(__name__)

class ResourceOverviewView(RestrictedView):
    """View to display active compute pools
    """
    template_name = 'account/resource_overview.html'
    page_title = 'AWS Resource Overview'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        #Get list of resources
        
        keys = AWSAccessKey.objects.filter(user=request.user)
        
        overview=[]
        
        for key in keys:
            recognized_resources=resource_management_tools.get_recognized_resources(user=request.user, key=key)
            unrecognized_resources = resource_management_tools.get_unrecognized_resources(user=request.user,key=key)
            overview.append((key, recognized_resources, unrecognized_resources))
            
            
        kwargs['overview'] = overview
        return super(ResourceOverviewView, self).dispatch(request, *args, **kwargs)


class ResourceTerminateView(RestrictedView):
    page_title = 'Confirm termination of AWS resources'
    template_name = 'account/resource_terminate.html'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        #Get list of resources
        
        if kwargs['all_unrecognized']:
            resources = resource_management_tools.get_unrecognized_resources(request.user)
        else:
            key_id = kwargs['key_id']
            key=AWSAccessKey.objects.get(id=key_id)
            assert key.user == request.user
            resources = resource_management_tools.get_unrecognized_resources(request.user, key)
        
        if kwargs['confirmed']:
            resource_management_tools.terminate(request.user, resources)
        
        return HttpResponseRedirect(reverse_lazy('my_account_home'))

        
        kwargs['resources'] = resources
        return super(ResourceTerminateView, self).dispatch(request, *args, **kwargs)
