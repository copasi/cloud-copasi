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
from cloud_copasi.web_interface.aws import vpc_tools, aws_tools, ec2_tools
from cloud_copasi.web_interface import models
from boto.exception import EC2ResponseError, BotoServerError
from cloud_copasi.web_interface.models import VPC

class PoolStatusView(RestrictedView):
    """View to display active compute pools
    """
    template_name = 'pool/pool_status.html'
    page_title = 'Pool status'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        
        vpcs = VPC.objects.filter(access_key__user=request.user)
        if vpcs.count() == 0:
            request.session['errors'] = [('No active VPCs', 'You must have at least one active VPC configured before you can start a compute pool')]
            return HttpResponseRedirect(reverse_lazy('vpc_status'))
        pools = models.CondorPool.objects.filter(vpc__access_key__user=request.user)
        kwargs['pools'] = pools
        return RestrictedView.dispatch(self, request, *args, **kwargs)
    
class AddPoolForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(AddPoolForm, self).__init__(*args, **kwargs)
        
        vpc_choices = models.VPC.objects.filter(access_key__user=user).values_list('id', 'access_key__name')
        self.fields['vpc'].choices=vpc_choices
        
    def clean(self):
        cleaned_data = super(AddPoolForm, self).clean()
        name = cleaned_data.get('name')
        vpc = cleaned_data.get('vpc')
        if vpc == None:
            raise forms.ValidationError('You must select a valid access key with an associated VPC.')

        if CondorPool.objects.filter(name=name,vpc__access_key__user=vpc.access_key.user).count() > 0:
            raise forms.ValidationError('A pool with this name already exists')
        return cleaned_data


    class Meta:
        model = CondorPool
        fields = ('name', 'vpc', 'size', 'initial_instance_type')
        widgets = {
            'initial_instance_type' : forms.Select(attrs={'style':'width:30em'}),
            
            }

class PoolAddView(RestrictedFormView):
    template_name = 'pool/pool_add.html'
    page_title = 'Add pool'
    success_url = reverse_lazy('pool_status')
    form_class = AddPoolForm
    
    
    def get_form_kwargs(self):
        kwargs =  super(RestrictedFormView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        
        return kwargs
    
    def form_valid(self, *args, **kwargs):
        form=kwargs['form']
        
        try:
            pool = form.save()
            
            key_pair=ec2_tools.create_key_pair(pool)
            pool.key_pair = key_pair
        except Exception, e:
            self.request.session['errors'] = aws_tools.process_errors([e])
            return HttpResponseRedirect(reverse_lazy('pool_add'))
        pool.save()
        
        #Launch the pool
        #try:
        ec2_tools.launch_pool(pool)
        #except Exception, e:
        #    self.request.session['errors'] = aws_tools.process_errors([e])
        #    return HttpResponseRedirect(reverse_lazy('pool_add'))
        
        return super(PoolAddView, self).form_valid(*args, **kwargs)

    def dispatch(self, *args, **kwargs):
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Launching pool'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. Launching a pool can take several minutes'

        return super(PoolAddView, self).dispatch(*args, **kwargs)

class PoolDetailsView(RestrictedView):
    template_name='pool/pool_details.html'
    page_title = 'Comnpute pool details'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        pool_id = kwargs['pool_id']
        try:
            condor_pool = CondorPool.objects.get(id=pool_id)
            assert condor_pool.vpc.access_key.user == request.user
        except EC2ResponseError, e:
            request.session['errors'] = [error for error in e.errors]
            return HttpResponseRedirect(reverse_lazy('pool_status'))
        except Exception, e:
            self.request.session['errors'] = [e]
            return HttpResponseRedirect(reverse_lazy('p'))
        
        instances=EC2Instance.objects.filter(condor_pool=condor_pool)
        
        try:
            master_id = condor_pool.master.id
        except:
            master_id=None
        
        compute_instances = instances.exclude(id=master_id)
        
        kwargs['instances'] = instances
        kwargs['compute_instances'] = compute_instances
        kwargs['condor_pool'] = condor_pool

        return super(PoolDetailsView, self).dispatch(request, *args, **kwargs)
    
class PoolTerminateView(RestrictedView):
    template_name='pool/pool_terminate.html'
    page_title='Confirm pool termination'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        pool_id = kwargs['pool_id']
        
        confirmed= kwargs['confirmed']
        
        condor_pool = CondorPool.objects.get(id=pool_id)
        assert condor_pool.vpc.access_key.user == request.user
        
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Terminating pool'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. Terminating a pool can take several minutes'
        
        if not confirmed:
        
            kwargs['condor_pool'] = condor_pool
            
            return super(PoolTerminateView, self).dispatch(request, *args, **kwargs)
        else:
            #Terminate the pool
            errors = ec2_tools.terminate_pool(condor_pool)
            request.session['errors']=errors
            return HttpResponseRedirect(reverse_lazy('pool_status'))

class PoolScaleUpForm(forms.Form):
    
    nodes_to_add = forms.IntegerField(required=False)
    total_pool_size = forms.IntegerField(required=False)
    

    def clean(self):
        cleaned_data = super(PoolScaleUpForm, self).clean()
        nodes_to_add = cleaned_data.get('nodes_to_add')
        total_pool_size = cleaned_data.get('total_pool_size')
        if (not nodes_to_add) and (not total_pool_size):
            raise forms.ValidationError('You must enter a value.')
        if nodes_to_add and total_pool_size:
            raise forms.ValidationError('You must enter only one value.')
        if nodes_to_add:
            try:
                assert nodes_to_add > 0
            except:
                raise forms.ValidationError('You must enter a value greater than 0.')

        if total_pool_size:
            try:
                assert total_pool_size > 0
            except:
                raise forms.ValidationError('You must enter a value greater than 0.')

        return cleaned_data



class PoolScaleUpView(RestrictedFormView):
    template_name = 'pool/pool_scale.html'
    page_title = 'Scale up pool'
    success_url = reverse_lazy('pool_status')
    form_class = PoolScaleUpForm

    
    
    def form_valid(self, *args, **kwargs):
        try:
            form=kwargs['form']
            user=kwargs['request'].user
            condor_pool = CondorPool.objects.get(id=kwargs['pool_id'])
            
            if form.cleaned_data['nodes_to_add']:
                extra_nodes = form.cleaned_data['nodes_to_add']
            else:
                extra_nodes = form.cleaned_data['total_pool_size'] - EC2Instance.objects.filter(condor_pool=condor_pool).count()
            
            ec2_tools.scale_up(condor_pool, extra_nodes)
            condor_pool.save()
        except Exception, e:
            self.request.session['errors'] = aws_tools.process_errors([e])
            return HttpResponseRedirect(reverse_lazy('pool_status'))

        
        
        return super(PoolScaleUpView, self).form_valid(*args, **kwargs)

    def dispatch(self, *args, **kwargs):
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Scaling pool'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. This process can take several minutes'
        kwargs['scale_up']=True
        return super(PoolScaleUpView, self).dispatch(*args, **kwargs)
