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
from cloud_copasi.web_interface.models import AWSAccessKey, VPCConnection, CondorPool, EC2Instance,\
    EC2Pool, BoscoPool
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
import sys
from django.contrib.auth.forms import PasswordChangeForm
from cloud_copasi.web_interface.aws import vpc_tools, aws_tools, ec2_tools
from cloud_copasi.web_interface import models
from boto.exception import EC2ResponseError, BotoServerError
from cloud_copasi.web_interface.models import VPC
import logging

log = logging.getLogger(__name__)

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
        pools = models.CondorPool.objects.filter(user=request.user)
        kwargs['pools'] = pools
        
        ec2_pools = EC2Pool.objects.filter(user=request.user)
        
        for ec2_pool in ec2_pools:
            ec2_tools.refresh_pool(ec2_pool)
        
        kwargs['ec2_pools'] = ec2_pools
        
        return RestrictedView.dispatch(self, request, *args, **kwargs)
    
class AddEC2PoolForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(AddEC2PoolForm, self).__init__(*args, **kwargs)
        
        vpc_choices = models.VPC.objects.filter(access_key__user=user).values_list('id', 'access_key__name')
        self.fields['vpc'].choices=vpc_choices
        
    def clean(self):
        cleaned_data = super(AddEC2PoolForm, self).clean()
        name = cleaned_data.get('name')
        vpc = cleaned_data.get('vpc')
        if vpc == None:
            raise forms.ValidationError('You must select a valid access key with an associated VPC.')

        if CondorPool.objects.filter(name=name,user=vpc.access_key.user).count() > 0:
            raise forms.ValidationError('A pool with this name already exists')
        
        return cleaned_data


    class Meta:
        model = EC2Pool
        fields = ('name', 'vpc', 'size', 'initial_instance_type', 'auto_terminate')
        widgets = {
            'initial_instance_type' : forms.Select(attrs={'style':'width:30em'}),
            
            }

class EC2PoolAddView(RestrictedFormView):
    template_name = 'pool/ec2_pool_add.html'
    page_title = 'Add EC2 pool'
    success_url = reverse_lazy('pool_status')
    form_class = AddEC2PoolForm
    
    
    def get_form_kwargs(self):
        kwargs =  super(RestrictedFormView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        
        return kwargs
    
    def form_valid(self, *args, **kwargs):
        form=kwargs['form']
        
        try:
            pool = form.save(commit=False)
            pool.user = pool.vpc.access_key.user
            
            
            key_pair=ec2_tools.create_key_pair(pool)
            pool.key_pair = key_pair
        except Exception, e:
            log.exception(e)
            self.request.session['errors'] = aws_tools.process_errors([e])
            return HttpResponseRedirect(reverse_lazy('ec2_pool_add'))
        pool.save()
        
        #Launch the pool
        #try:
        ec2_tools.launch_pool(pool)
        pool.save()
        #except Exception, e:
        #    self.request.session['errors'] = aws_tools.process_errors([e])
        #    return HttpResponseRedirect(reverse_lazy('pool_add'))
        
        return super(EC2PoolAddView, self).form_valid(*args, **kwargs)

    def dispatch(self, *args, **kwargs):
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Launching pool'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. Launching a pool can take several minutes'

        return super(EC2PoolAddView, self).dispatch(*args, **kwargs)

class EC2PoolDetailsView(RestrictedView):
    template_name='pool/ec2_pool_details.html'
    page_title = 'EC2 pool details'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        pool_id = kwargs['pool_id']
        try:
            ec2_pool = EC2Pool.objects.get(id=pool_id)
            assert ec2_pool.vpc.access_key.user == request.user
            ec2_tools.refresh_pool(ec2_pool)
        except EC2ResponseError, e:
            request.session['errors'] = [error for error in e.errors]
            log.exception(e)
            return HttpResponseRedirect(reverse_lazy('pool_status'))
        except Exception, e:
            self.request.session['errors'] = [e]
            log.exception(e)
            return HttpResponseRedirect(reverse_lazy('p'))
        
        instances=EC2Instance.objects.filter(ec2_pool=ec2_pool)
        
        try:
            master_id = ec2_pool.master.id
        except:
            master_id=None
        
        compute_instances = instances.exclude(id=master_id)
        
        kwargs['instances'] = instances
        kwargs['compute_instances'] = compute_instances
        kwargs['ec2_pool'] = ec2_pool

        return super(EC2PoolDetailsView, self).dispatch(request, *args, **kwargs)
    
class EC2PoolTerminateView(RestrictedView):
    template_name='pool/ec2_pool_terminate.html'
    page_title='Confirm EC2 pool termination'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        pool_id = kwargs['pool_id']
        
        confirmed= kwargs['confirmed']
        
        ec2_pool = EC2Pool.objects.get(id=pool_id)
        assert ec2_pool.vpc.access_key.user == request.user
        ec2_tools.refresh_pool(ec2_pool)
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Terminating pool'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. Terminating a pool can take several minutes'
        
        if not confirmed:
        
            kwargs['ec2_pool'] = ec2_pool
            
            return super(EC2PoolTerminateView, self).dispatch(request, *args, **kwargs)
        else:
            #Terminate the pool
            errors = ec2_tools.terminate_pool(ec2_pool)
            request.session['errors']=errors
            return HttpResponseRedirect(reverse_lazy('pool_status'))

class EC2PoolScaleUpForm(forms.Form):
    
    nodes_to_add = forms.IntegerField(required=False)
    total_pool_size = forms.IntegerField(required=False)
    

    def clean(self):
        cleaned_data = super(EC2PoolScaleUpForm, self).clean()
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



class EC2PoolScaleUpView(RestrictedFormView):
    template_name = 'pool/ec2_pool_scale.html'
    page_title = 'Scale up EC2 pool'
    success_url = reverse_lazy('pool_status')
    form_class = EC2PoolScaleUpForm

    
    
    def form_valid(self, *args, **kwargs):
        try:
            form=kwargs['form']
            user=self.request.user
            ec2_pool = EC2Pool.objects.get(id=kwargs['pool_id'])
            assert ec2_pool.vpc.access_key.user == self.request.user
            ec2_tools.refresh_pool(ec2_pool)
            if form.cleaned_data['nodes_to_add']:
                extra_nodes = form.cleaned_data['nodes_to_add']
            else:
                extra_nodes = form.cleaned_data['total_pool_size'] - EC2Instance.objects.filter(ec2_pool=ec2_pool).count()
            
            ec2_tools.scale_up(ec2_pool, extra_nodes)
            ec2_pool.save()
        except Exception, e:
            self.request.session['errors'] = aws_tools.process_errors([e])
            log.exception(e)
            return HttpResponseRedirect(reverse_lazy('pool_status'))

        
        
        return super(EC2PoolScaleUpView, self).form_valid(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Scaling pool'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. This process can take several minutes'
        kwargs['scale_up']=True
        ec2_pool = EC2Pool.objects.get(id=kwargs['pool_id'])
        assert ec2_pool.vpc.access_key.user == request.user
        ec2_tools.refresh_pool(ec2_pool)
        
        return super(EC2PoolScaleUpView, self).dispatch(request, *args, **kwargs)

class AddBoscoPoolForm(forms.Form):
        
    name = forms.CharField(max_length=100, label='Pool name', help_text='Choose a name for this pool')
    
    address = forms.CharField(max_length=200, help_text='The address or IP of the remote submit node (e.g. server.campus.edu or 86.3.3.2)')
    
    username = forms.CharField(max_length=50, help_text='The username used to log in to the remote submit node')
    
    pool_type = forms.ChoiceField(choices = (
                                                           ('condor', 'Condor'),
                                                           ('pbs', 'PBS'),
                                                           ('lsf', 'LSF'),
                                                           ('sge', 'Sun Grid Engine'),
                                                           ),
                                 initial='condor',
                                 )
    
    platform = forms.ChoiceField(label='Remote platform',
                                 help_text='The platform of the remote submitter we are connecting to',
                                choices = (
                                           ('DEB6', 'Debian 6'),
                                           ('RH5', 'Red Hat 5'),
                                           ('RH6', 'Red Hat 6'),
                                           ),
                                initial='DEB6',
                                )

    ssh_key = forms.CharField(max_length = 10000,
                              label = 'SSH Key',
                              help_text = 'A working private SSH key for the pool submit node. This key will used only once, and will not be stored. See the documentation for full details on how to generate this.',
                              widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        return super(AddBoscoPoolForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(AddBoscoPoolForm, self).clean()
        name = cleaned_data.get('name')
        vpc = cleaned_data.get('user')
        address = cleaned_data.get('address')
        
        if BoscoPool.objects.filter(name=name,user=self.user).count() > 0:
            raise forms.ValidationError('A pool with this name already exists')

        return cleaned_data
        
class BoscoPoolAddView(RestrictedFormView):
    
    page_title = 'Add existing compute pool'
    form_class = AddBoscoPoolForm
    template_name = 'pool/ec2_pool_add.html'
    success_url = reverse_lazy('pool_status')
    
    def get_form_kwargs(self):
        kwargs = super(BoscoPoolAddView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
