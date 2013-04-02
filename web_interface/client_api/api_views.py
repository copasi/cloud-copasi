from django.http import HttpResponse, HttpResponseForbidden, HttpResponseServerError
from django.views.generic import TemplateView, RedirectView, View, FormView
from django.views.generic.edit import FormMixin, ProcessFormView
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from django import forms
from web_interface.views import RestrictedView, DefaultView, RestrictedFormView
from models import AWSAccessKey
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
import sys
from django.contrib.auth.forms import PasswordChangeForm
from web_interface.aws import vpc_tools, aws_tools
from web_interface import models
from django.views.decorators.cache import never_cache
from boto.exception import EC2ResponseError, BotoServerError
import boto.exception
from web_interface.models import VPC, CondorPool
from django.http import HttpRequest
import json
from django.views.decorators.csrf import csrf_exempt

class APIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(APIView, self).dispatch(request, *args, **kwargs)


class UpdateJobStatusView(APIView):
    """
    Update the status of a particular job without changing the status of individual condor jobs
    """
    
    def post(self, request, *args, **kwargs):
        pass

class RegisterJobView(APIView):
    """
    Register the queue ids of condor jobs
    """ 

    def post(self, request, *args, **kwargs):
        assert isinstance(request, HttpRequest)
        assert request.META['CONTENT_TYPE'] == 'application/json'
        
        json_data=request.body
        data = json.loads(json_data)
        
        pool_id = data['pool_id']
        secret_key = data['secret_key']
        
        pool=CondorPool.objects.get(id=pool_id)
        #Validate that we trust this pool
        assert pool.secret_key == secret_key
        
        print>>sys.stderr, data
        
        
        #Construct a json response to send back
        response_data={'status':'created'}
        json_response=json.dumps(response_data)
        
        return HttpResponse(json_response, content_type="application/json", status=201)
    
class UpdateStatusView(APIView):
    """
    Update the queue ids of condor jobs
    """ 
    

    def post(self, request, *args, **kwargs):
        assert isinstance(request, HttpRequest)
        assert request.META['CONTENT_TYPE'] == 'application/json'
        json_data=request.body
        data = json.loads(json_data)
        

        #Construct a json response to send back
        response_data={'status':'created'}
        json_response=json.dumps(response_data)
        
        return HttpResponse(json_response, content_type="application/json", status=201)
