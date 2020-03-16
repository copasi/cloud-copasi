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
from django.urls import reverse_lazy
from django import forms
from cloud_copasi.web_interface.views import RestrictedView, DefaultView, RestrictedFormView
from cloud_copasi.web_interface.models import PLATFORM_CHOICES, POOL_TYPE_CHOICES, AWSAccessKey,\
    VPCConnection, CondorPool, EC2Instance, EC2Pool, BoscoPool, Task, SpotRequest
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
import sys
from django.contrib.auth.forms import PasswordChangeForm
from cloud_copasi.web_interface.aws import vpc_tools, aws_tools, ec2_tools,\
    ec2_config
from cloud_copasi.web_interface.pools import condor_tools
from cloud_copasi.web_interface import models
from boto.exception import EC2ResponseError, BotoServerError
from cloud_copasi.web_interface.models import VPC
import logging
import tempfile, subprocess
from django.core.validators import RegexValidator
import os
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.utils import ErrorList
from django.http.response import HttpResponseRedirect
from django.contrib.auth.models import User
from cloud_copasi.web_interface.email import email_tools

log = logging.getLogger(__name__)

class PoolListView(RestrictedView):
    """View to display active compute pools
    """
    template_name = 'pool/pool_list.html'
    page_title = 'Compute pools'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        
        
        ec2_pools = EC2Pool.objects.filter(user=request.user, copy_of__isnull=True)
        
        for ec2_pool in ec2_pools:
            ec2_tools.refresh_pool(ec2_pool)
        
        kwargs['ec2_pools'] = ec2_pools
        
        
        bosco_pools = BoscoPool.objects.filter(user=request.user, copy_of__isnull=True)
        kwargs['bosco_pools'] = bosco_pools
        
        
        shared_pools = CondorPool.objects.filter(user=request.user, copy_of__isnull=False)
        kwargs['shared_pools'] = shared_pools
        
        
        return RestrictedView.dispatch(self, request, *args, **kwargs)
    


class PoolRenameForm(forms.Form):
    new_name =forms.CharField(max_length=100)
    
class PoolRenameView(RestrictedFormView):
    page_title='Rename pool'
    template_name = 'pool/pool_rename.html'
    form_class = PoolRenameForm
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        pool = CondorPool.objects.get(id=kwargs['pool_id'])
        assert pool.user == request.user
        kwargs['pool'] = pool
        return super(PoolRenameView, self).dispatch(request, *args, **kwargs)
    
    def form_valid(self, *args, **kwargs):
        
        form = kwargs['form']
        new_name = form.cleaned_data['new_name']
        pool = CondorPool.objects.get(id=kwargs['pool_id'])
        assert pool.user == self.request.user 
        
        existing_pools = CondorPool.objects.filter(user=self.request.user).filter(name=new_name)
        
        if existing_pools.count()>0:
            form._errors[NON_FIELD_ERRORS] = ErrorList(['A pool with this name already exists'])
            return self.form_invalid(self, *args, **kwargs)
        
        pool.name = new_name
        pool.save()
        self.success_url = reverse_lazy('pool_details', kwargs={'pool_id': kwargs['pool_id']})
        return super(PoolRenameView, self).form_valid(*args, **kwargs)



class AddEC2PoolForm(forms.Form):
    
    name = forms.CharField(max_length=100, label='Pool name', help_text='Choose a name for this pool')
    
    vpc = forms.ChoiceField(label = 'Keypair')
    
    initial_instance_type = forms.ChoiceField(choices=ec2_config.EC2_TYPE_CHOICES,
                                              initial='m1.medium',
                                              widget=forms.widgets.Select(attrs={'style':'width:30em'}),
                                              help_text='The instance type to launch. The price per hour will vary depending on the instance type. For more information on the different instance types see the <a href="http://aws.amazon.com/ec2/pricing/#on-demand" target="new">AWS documentation</a>.')
    
    size = forms.IntegerField(min_value=0, label='Initial number of nodes', help_text='The number of compute nodes to launch. In addition, a master node will also be launched.')
        
    pricing = forms.ChoiceField(choices= (('fixed', 'Fixed price'),
                                             ('spot', 'Spot price bidding')),
                                   widget=forms.RadioSelect(),
                                   initial='fixed',
                                   help_text='Spot price bidding can significantly reduce running costs, however your instances will be terminated while your bid price remains below the market price. Note that the Master node will always launch as a fixed price instance. The current spot price is displayed below. For information on fixed instance pricing, refer to the <a href="http://aws.amazon.com/ec2/pricing/#on-demand" target="new">AWS documentation</a>. Note that all instances are launched in the US-East (N. Virginia) AWS region.')
    
    spot_bid_price = forms.DecimalField(required=False, label='Spot price bid ($) per hour', help_text = 'Your maximum spot price bid in US Dollars per hour. Note that this does not include VAT or any other applicable taxes.',
                                        max_digits=5, decimal_places=3, initial=0.000,
                                        )
    
    auto_terminate = forms.BooleanField(help_text = 'Terminate the pool after a task completed if no other tasks are queued. Only applies after at least one task has been submitted to the pool.', required=False)
    smart_terminate = forms.BooleanField(help_text = 'Terminate individual compute nodes after they have been idle (CPU usage <=%d%%) for %d consecutive periods of %d minutes. This applies whether or not a task has been submitted to the pool.' % (ec2_config.DOWNSCALE_CPU_THRESHOLD, ec2_config.DOWNSCALE_CPU_EVALUATION_PERIODS, ec2_config.DONWSCALE_CPU_PERIOD/60,), required=False)

    def clean_spot_bid_price(self):
        value = self.cleaned_data['spot_bid_price']
        spot_price_checked = (self.cleaned_data['pricing'] == 'spot')
        if value <= 0 and spot_price_checked:
            raise forms.ValidationError('Bid price must be greater than 0')
        else:
            return value
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(AddEC2PoolForm, self).__init__(*args, **kwargs)
        
        vpc_choices = models.VPC.objects.filter(access_key__user=user).values_list('id', 'access_key__name')
        self.fields['vpc'].choices=vpc_choices
        
    def clean(self):
        cleaned_data = super(AddEC2PoolForm, self).clean()
        name = cleaned_data.get('name')
        try:
            vpc = VPC.objects.get(id=cleaned_data.get('vpc'))
            cleaned_data['vpc'] = vpc
        except:
            raise forms.ValidationError('You must select a valid access key with an associated VPC.')
        
        if CondorPool.objects.filter(name=name,user=vpc.access_key.user).count() > 0:
            raise forms.ValidationError('A pool with this name already exists')
        
        return cleaned_data




class EC2PoolAddView(RestrictedFormView):
    template_name = 'pool/ec2_pool_add.html'
    page_title = 'Add EC2 pool'
    success_url = reverse_lazy('pool_list')
    form_class = AddEC2PoolForm
    
    
    def get_form_kwargs(self):
        kwargs =  super(RestrictedFormView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        
        return kwargs
    
    def form_valid(self, *args, **kwargs):
        form=kwargs['form']
        
        spot = (form.cleaned_data['pricing'] == 'spot')
        
        try:
            pool = EC2Pool(name = form.cleaned_data['name'],
                           vpc = form.cleaned_data['vpc'],
                           initial_instance_type = form.cleaned_data['initial_instance_type'],
                           size=form.cleaned_data['size'],
                           auto_terminate=form.cleaned_data['auto_terminate'],
                           smart_terminate=form.cleaned_data['smart_terminate'],
                           user = form.cleaned_data['vpc'].access_key.user,
                           spot_request=spot,
                           spot_price = form.cleaned_data['spot_bid_price']
                           )
            pool.save()
            
            key_pair=ec2_tools.create_key_pair(pool)
            pool.key_pair = key_pair
        except Exception as e:
            log.exception(e)
            self.request.session['errors'] = aws_tools.process_errors([e])
            return HttpResponseRedirect(reverse_lazy('ec2_pool_add'))
        pool.save()
        
        #Launch the pool
        try:
            errors = ec2_tools.launch_pool(pool)
            pool.save()
        
            #Connect to Bosco
            condor_tools.add_ec2_pool(pool)
        except Exception as e:
            log.exception(e)
            self.request.session['errors'] = aws_tools.process_errors([e])
            return HttpResponseRedirect(reverse_lazy('pool_details', kwargs={'pool_id':pool.id}))
        
        if errors != []:
            self.request.session['errors'] = aws_tools.process_errors(errors)
            return HttpResponseRedirect(reverse_lazy('pool_details', kwargs={'pool_id': pool.id}))
        self.success_url = reverse_lazy('pool_test', kwargs={'pool_id':pool.id})
        
        return super(EC2PoolAddView, self).form_valid(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Launching pool'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. Launching a pool can take several minutes'
        
        #Get an aws key for this user. For the time being, just use the first one in the list
        user = request.user
        keys = AWSAccessKey.objects.filter(user=user)
        if keys.count() > 0:
            kwargs['key_id'] = keys[0].id
        
        return super(EC2PoolAddView, self).dispatch(request, *args, **kwargs)

class EC2PoolTerminationSettingsForm(forms.Form):
    auto_terminate = forms.BooleanField(help_text = 'Terminate the pool after a task completed if no other tasks are queued. Only applies after at least one task has been submitted to the pool.', required=False)
    smart_terminate = forms.BooleanField(help_text = 'Terminate individual compute nodes after they have been idle (CPU usage <=%d%%) for %d consecutive periods of %d minutes. This applies whether or not a task has been submitted to the pool.' % (ec2_config.DOWNSCALE_CPU_THRESHOLD, ec2_config.DOWNSCALE_CPU_EVALUATION_PERIODS, ec2_config.DONWSCALE_CPU_PERIOD/60,), required=False)
    
    
    
class EC2PoolTerminationSettingsView(RestrictedFormView):
    page_title='Rename pool'
    template_name = 'pool/pool_termination.html'
    form_class = EC2PoolTerminationSettingsForm
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        pool = EC2Pool.objects.get(id=kwargs['pool_id'])
        assert pool.user == request.user
        kwargs['pool'] = pool
        
        self.initial['auto_terminate'] = pool.auto_terminate
        self.initial['smart_terminate'] = pool.smart_terminate
        
        return super(EC2PoolTerminationSettingsView, self).dispatch(request, *args, **kwargs)
    
        
        
    def form_valid(self, *args, **kwargs):
        
        form = kwargs['form']
        auto_terminate = form.cleaned_data['auto_terminate']
        smart_terminate = form.cleaned_data['smart_terminate']
        
        pool = EC2Pool.objects.get(id=kwargs['pool_id'])
        assert pool.user == self.request.user 
        
        if pool.smart_terminate ==True and smart_terminate == False:
            #In this case we have to remove instance alarms
            errors = ec2_tools.remove_instances_alarms(pool)
            
            if errors != []:
                self.request.session['errors'] = aws_tools.process_errors([errors])
        
        pool.auto_terminate = auto_terminate
        pool.smart_terminate = smart_terminate
        
        pool.save()
        self.success_url = reverse_lazy('pool_details', kwargs={'pool_id': kwargs['pool_id']})
        return super(EC2PoolTerminationSettingsView, self).form_valid(*args, **kwargs)


class PoolDetailsView(RestrictedView):
    template_name='pool/pool_details.html'
    page_title = 'Pool details'
        
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        
        pool = CondorPool.objects.get(id=kwargs['pool_id'])
        
        #Recast the pool type
        if pool.get_pool_type() == 'ec2':
            pool = EC2Pool.objects.get(id=pool.id)
        elif pool.get_pool_type() == 'bosco':
            pool = BoscoPool.objects.get(id=pool.id)
        
        kwargs['pool'] = pool
        
        
        assert isinstance(pool, CondorPool)
        assert pool.user == self.request.user
        
        if pool.copy_of != None:
            pool_type = 'shared'
            #Recast the original pool type to be the same as the current pool type
            original_pool = pool.__class__.objects.get(id=pool.copy_of.id)
            kwargs['original_pool'] = original_pool
        elif pool.get_pool_type() == 'ec2':
            pool_type = 'ec2'
            kwargs['original_pool'] = pool
        else:
            pool_type = 'bosco'
            
        kwargs['pool_type'] = pool_type
        
        tasks = Task.objects.filter(condor_pool=pool)
        kwargs['tasks']=tasks

        
        #Decide on which buttons to display
        buttons = {}
        #All pools have the following:
        buttons[0] = {'button_text': 'Remove pool', #Rename this later for EC2 pools
                      'url': reverse_lazy('pool_remove', kwargs={'pool_id' : kwargs['pool_id']}),
                      'class':'button button-narrow button-alt',
                      }
        
        buttons[1] = {'button_text' : 'Test pool',
                      'url': reverse_lazy('pool_test_result', kwargs={'pool_id' : kwargs['pool_id']}),
                      'loading_screen': True,
                      }
        
        if pool_type != 'shared':
            buttons[2] = {'button_text' : 'Share pool',
                          'url': reverse_lazy('pool_share', kwargs={'pool_id' : kwargs['pool_id']}),
                          }
        
        buttons[3] = {'button_text' : 'Rename pool',
                      'url': reverse_lazy('pool_rename', kwargs={'pool_id' : kwargs['pool_id']}),
                       }
        
        if pool_type != 'shared' and pool_type != 'bosco':
            buttons[4] = {'button_text' : 'Scale up',
                      'url': reverse_lazy('ec2_pool_scale_up', kwargs={'pool_id' : kwargs['pool_id']}),
                       }
            buttons[5] = {'button_text' : 'Scale down',
                      'url': reverse_lazy('ec2_pool_scale_down', kwargs={'pool_id' : kwargs['pool_id']}),
                       }
            
            buttons[6] = {'button_text' : 'Change termination settings',
                      'url': reverse_lazy('pool_termination_settings', kwargs={'pool_id' : kwargs['pool_id']}),
                       }
        if pool_type != 'shared' and pool_type == 'bosco':
            buttons[4] = {'button_text' : 'Change status page link',
                          'url': reverse_lazy('pool_link_change',
                          kwargs={'pool_id' : kwargs['pool_id']})}
        
        if pool_type == 'shared':
            kwargs['shared'] = True
            
            if original_pool.get_pool_type() == 'ec2':
                kwargs['shared_pool_type'] = 'ec2'
                instances=EC2Instance.objects.filter(ec2_pool=original_pool)
            
                try:
                    master_id = original_pool.master.id
                except:
                    master_id=None
            
                compute_instances = instances.exclude(id=master_id)
        
                kwargs['instances'] = instances
                kwargs['compute_instances'] = compute_instances
    #            kwargs['ec2_pool'] = ec2_pool
                
            else:
                kwargs['shared_pool_type'] = 'bosco'
            
        
        
        elif pool_type == 'ec2':
            #Recast the pool as an EC2 object
            pool = EC2Pool.objects.get(id=pool.id)
            kwargs['pool'] = pool
            buttons[0]['button_text'] = 'Terminate pool'
            
            try:
                assert pool.vpc.access_key.user == request.user
                ec2_tools.refresh_pool(pool)
            except EC2ResponseError as e:
                request.session['errors'] = [error for error in e.errors]
                log.exception(e)
                return HttpResponseRedirect(reverse_lazy('pool_list'))
            except Exception as e:
                self.request.session['errors'] = [e]
                log.exception(e)
                return HttpResponseRedirect(reverse_lazy('pool_list'))
            
            instances=EC2Instance.objects.filter(ec2_pool=pool)
            active_instances = instances.filter(state='running')
            not_terminated_instances = instances.exclude(state='terminated').exclude(instance_role='master')
            terminated_instances = instances.filter(state='terminated')
            
            spot_requests = SpotRequest.objects.filter(ec2_pool=pool)
            fulfilled_spot_requests = spot_requests.filter(status_code='fulfilled')
            
            try:
                master_id = pool.master.id
            except:
                master_id=None
            
            compute_instances = instances.exclude(id=master_id)
            
            kwargs['instances'] = instances
            kwargs['active_instances']= active_instances
            kwargs['not_terminated_instances'] = not_terminated_instances
            kwargs['terminated_instances'] = terminated_instances
            kwargs['compute_instances'] = compute_instances
            kwargs['spot_requests'] = spot_requests
            kwargs['fulfilled_spot_requests'] = fulfilled_spot_requests
        else:
            #Pool type is bosco
            pass
        
        
        
        
        #Text for pool test screen
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Testing pool'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. Testing a pool can take several minutes.'
        kwargs['buttons'] = buttons
        
        return super(PoolDetailsView, self).dispatch(request, *args, **kwargs)

    
class EC2PoolScaleUpForm(forms.Form):
    
    instances_to_add = forms.IntegerField(required=True, min_value=1)
    
    initial_instance_type = forms.ChoiceField(choices=ec2_config.EC2_TYPE_CHOICES,
                                              initial='m1.medium',
                                              label='Instance type',
                                              widget=forms.widgets.Select(attrs={'style':'width:30em'}),
                                              help_text='The instance type to launch. The price per hour will vary depending on the instance type. For more information on the different instance types see the <a href="">help page</a>.')
    
    pricing = forms.ChoiceField(choices= (('fixed', 'Fixed price'),
                                             ('spot', 'Spot price bidding')),
                                   widget=forms.RadioSelect(),
                                   initial='fixed',
                                   help_text='Spot price bidding can significantly reduce running costs, however your instances will be terminated while your bid price remains below the market price. Note that the Master node will always launch as a fixed price instance.')
    
    spot_bid_price = forms.DecimalField(required=False, label='Spot price bid ($) per hour', help_text = 'Your maximum spot price bid in US Dollars per hour. Note that this does not include VAT or any other applicable taxes.',
                                        max_digits=5, decimal_places=3, initial=0.000,
                                        )


    def clean_spot_bid_price(self):
        price = self.cleaned_data['spot_bid_price']
        if self.cleaned_data['pricing'] == 'spot':
            if price <= 0:
                raise forms.ValidationError('Custom bid price must be greater than 0')
        return price

class EC2PoolScaleUpView(RestrictedFormView):
    template_name = 'pool/ec2_pool_scale_up.html'
    page_title = 'Scale up EC2 pool'
    success_url = reverse_lazy('pool_list')
    form_class = EC2PoolScaleUpForm

    
    
    def form_valid(self, *args, **kwargs):
        try:
            form=kwargs['form']
            user=self.request.user
            ec2_pool = EC2Pool.objects.get(id=kwargs['pool_id'])
            assert ec2_pool.vpc.access_key.user == self.request.user
            ec2_tools.refresh_pool(ec2_pool)
            extra_nodes=form.cleaned_data['instances_to_add']
            spot_price = form.cleaned_data['pricing'] == 'spot'
            spot_bid_price = form.cleaned_data['spot_bid_price']
            instance_type = form.cleaned_data['initial_instance_type']
            
            errors = ec2_tools.scale_up(ec2_pool=ec2_pool,
                               extra_nodes=extra_nodes,
                               instance_type=instance_type,
                               spot=spot_price,
                               spot_bid_price=spot_bid_price)
            ec2_pool.save()
            self.request.session['errors'] = aws_tools.process_errors(errors)

        except Exception as e:
            self.request.session['errors'] = aws_tools.process_errors([e])
            log.exception(e)
            return HttpResponseRedirect(reverse_lazy('pool_details', kwargs={'pool_id':ec2_pool.id}))

        
        self.success_url = reverse_lazy('pool_details', kwargs={'pool_id':ec2_pool.id})
        return super(EC2PoolScaleUpView, self).form_valid(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Scaling pool'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. This process can take several minutes'
        kwargs['scale_up']=True
        ec2_pool = EC2Pool.objects.get(id=kwargs['pool_id'])
        kwargs['pool'] = ec2_pool 
        assert ec2_pool.vpc.access_key.user == request.user
        ec2_tools.refresh_pool(ec2_pool)
        
        return super(EC2PoolScaleUpView, self).dispatch(request, *args, **kwargs)

class EC2PoolScaleDownForm(forms.Form):
    
    nodes_to_terminate = forms.IntegerField(required=True,
                                            help_text='How many nodes should be terminated',
                                            min_value=1)
    
    instance_type = forms.ChoiceField(required=True,
                                      label='Instance type',
                                      help_text='Terminate specific instance types only. Leave blank to select all instance types',
                                      choices = (('-', '------'),) + ec2_config.EC2_TYPE_CHOICES,
                                      initial='-',
                                      )
        
    pricing = forms.ChoiceField(required=True,
                                    label='Pricing',
                                    help_text='Terminate fixed price or spot price instances',
                                    widget=forms.RadioSelect(),
                                    choices=(('fixed', 'Fixed price'),
                                             ('spot', 'Spot price')),
                                    initial='fixed')
    
    spot_price_order = forms.ChoiceField(label='Spot price ordering',
                                         required=False,
                                         help_text='If terminating spot instances, terminate cheapest or most expensive bids first. Alternatively select custom price, and enter a specific price below.',
                                         choices=(('lowest', 'Cheapest'),
                                                  ('highest', 'Most expensive'),
                                                  ('custom', 'Custom price ($)')),
                                         initial='lowest',
                                         widget=forms.RadioSelect())
    
    spot_price_custom = forms.DecimalField(label='Custom spot price',
                                         help_text='If terminating spot instances, terminate instances with a specific price if you have selected custom price above.',
                                         initial=0.0,
                                         required=False,
                                         decimal_places=3,
                                         max_digits=5)
    
    
    
                                      

    def clean_spot_price_custom(self):
        price = self.cleaned_data['spot_price_custom']
        if self.cleaned_data['spot_price_order'] == 'custom':
            if price <= 0:
                raise forms.ValidationError('Custom bid price must be greater than 0')
        return price
    
class EC2PoolScaleDownView(RestrictedFormView):
    template_name = 'pool/ec2_pool_scale_down.html'
    page_title = 'Scale up EC2 pool'
    success_url = reverse_lazy('pool_list')
    form_class = EC2PoolScaleDownForm

    
    
    def form_valid(self, *args, **kwargs):
        try:
            form=kwargs['form']
            user=self.request.user
            ec2_pool = EC2Pool.objects.get(id=kwargs['pool_id'])
            assert ec2_pool.vpc.access_key.user == self.request.user
            ec2_tools.refresh_pool(ec2_pool)
            
            nodes_to_terminate = form.cleaned_data['nodes_to_terminate']
            instance_type = form.cleaned_data['instance_type']
            if instance_type == '-': instance_type = None
            pricing = form.cleaned_data['pricing']
            spot_price_order = form.cleaned_data['spot_price_order']
            spot_price_custom = form.cleaned_data['spot_price_custom']
            
            
            errors = ec2_tools.scale_down(ec2_pool, nodes_to_terminate, instance_type, pricing, spot_price_order, spot_price_custom)
            ec2_pool.save()
            if errors:
                self.request.session['errors'] = aws_tools.process_errors(errors)
            self.success_url = reverse_lazy('pool_details', kwargs={'pool_id':ec2_pool.id})
        except Exception as e:
            self.request.session['errors'] = aws_tools.process_errors([e])
            log.exception(e)
            return HttpResponseRedirect(reverse_lazy('pool_details', kwargs={'pool_id':ec2_pool.id}))

        
        
        return super(EC2PoolScaleDownView, self).form_valid(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Scaling pool'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. This process can take several minutes'
        kwargs['scale_up']=True
        ec2_pool = EC2Pool.objects.get(id=kwargs['pool_id'])
        kwargs['pool'] = ec2_pool 

        assert ec2_pool.vpc.access_key.user == request.user
        ec2_tools.refresh_pool(ec2_pool)
        
        return super(EC2PoolScaleDownView, self).dispatch(request, *args, **kwargs)

class BoscoPoolStatusPageForm(forms.Form):
    status_page_link = forms.CharField(max_length=1000,
                                       required=False,
                                       label='Pool status page',
                                       help_text='Optional link to a status page for the pool to be displayed alongside the pool information')

class BoscoPoolStatusPageView(RestrictedFormView):
    page_title='Edit status page link'
    template_name = 'pool/pool_status_edit.html'
    form_class = BoscoPoolStatusPageForm
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        pool = BoscoPool.objects.get(id=kwargs['pool_id'])
        assert pool.user == request.user
        
        kwargs['pool'] = pool
        assert pool.get_pool_type() != 'ec2'
        self.initial['status_page_link'] = pool.status_page
        
        return super(BoscoPoolStatusPageView, self).dispatch(request, *args, **kwargs)
    
    def form_valid(self, *args, **kwargs):
        
        form = kwargs['form']
        link = form.cleaned_data['status_page_link']
        pool = BoscoPool.objects.get(id=kwargs['pool_id'])
        assert pool.user == self.request.user 
        assert pool.get_pool_type() != 'ec2'
        
        pool.status_page = link
        pool.save()
        self.success_url = reverse_lazy('pool_details', kwargs={'pool_id': kwargs['pool_id']})
        return super(BoscoPoolStatusPageView, self).form_valid(*args, **kwargs)




class AddBoscoPoolForm(forms.Form):
        
    name = forms.CharField(max_length=100, label='Pool name', help_text='Choose a name for this pool')
    
    address = forms.CharField(max_length=200,
                              help_text='The address or IP of the remote submit node (e.g. server.campus.edu or 86.3.3.2)',
                              validators=[RegexValidator(r'^[a-z0-9-.]+(:([0-9]+)){0,1}$')])
    
    username = forms.CharField(max_length=50, help_text='The username used to log in to the remote submit node',
                               validators=[RegexValidator(r'^[A-Za-z0-9]+(?:[_-][A-Za-z0-9]+)*$')])
    
    pool_type = forms.ChoiceField(choices = POOL_TYPE_CHOICES,
                                  initial = POOL_TYPE_CHOICES[0][0],
                                 ) 
    
    platform = forms.ChoiceField(label='Remote platform',
                                 help_text='The platform of the remote submitter we are connecting to. Not sure which to select? See the documentation for full details.',
                                 choices = PLATFORM_CHOICES,
                                 initial = PLATFORM_CHOICES[0][0],
                                )

    ssh_key = forms.CharField(max_length = 10000,
                              label = 'SSH private key',
                              help_text = 'A working SSH private key for the pool submit node. This key will used only once, and will not be stored. See the documentation for full details on how to generate this.',
                              widget=forms.Textarea)

    status_page_link = forms.CharField(max_length=1000,
                                       required=False,
                                       label='Pool status page',
                                       help_text='Optional link to a status page for the pool to be displayed alongside the pool information')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        return super(AddBoscoPoolForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(AddBoscoPoolForm, self).clean()
        name = cleaned_data.get('name')
        
        address = cleaned_data.get('address')
        username = cleaned_data.get('username')
        if BoscoPool.objects.filter(name=name,user=self.user).count() > 0:
            raise forms.ValidationError('A pool with this name already exists')
        
        return cleaned_data



        
class BoscoPoolAddView(RestrictedFormView):
    
    page_title = 'Add existing compute pool'
    form_class = AddBoscoPoolForm
    template_name = 'pool/bosco_pool_add.html'
    success_url = reverse_lazy('pool_list')
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Connecting to pool'
        kwargs['loading_description'] = 'Please do not navigate away from this page. Connecting to a pool can take several minutes.'
        
        return super(BoscoPoolAddView, self).dispatch(*args, **kwargs)

    
    
    def get_form_kwargs(self):
        kwargs = super(BoscoPoolAddView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, *args, **kwargs):
        
        #Firstly, check to see if the ssh credentials are valid
        form = kwargs['form']
        
        file_handle, ssh_key_filename = tempfile.mkstemp()
        
        ssh_key_file = open(ssh_key_filename, 'w')
        ssh_key_file.write(form.cleaned_data['ssh_key'])
        ssh_key_file.close()
        
        username = form.cleaned_data['username']
        address = form.cleaned_data['address']
        
        log.debug('Testing SSH credentials')
        command = ['ssh', '-o', 'StrictHostKeyChecking=no', '-i', ssh_key_filename, '-l', username, address, 'pwd']
        process = subprocess.Popen(command, stdout=subprocess.PIPE, env={'DISPLAY' : ''})
        output = process.communicate()
        
        log.debug('SSH response:')
        log.debug(output)
        
        if process.returncode != 0:
            os.remove(ssh_key_filename)

            form._errors[NON_FIELD_ERRORS] = ErrorList(['The SSH credentials provided are not correct'])
            return self.form_invalid(self, *args, **kwargs)
        
        #Assume the SSH credentails are good
        #Next, we try to add the pool using bosco_cluster --add
        
        ##Only do this if no other pools exist with the same address!
        
        if BoscoPool.objects.filter(address = username + '@' + address).count() == 0:
            output, errors, exit_status = condor_tools.add_bosco_pool(form.cleaned_data['platform'], username+'@'+address, ssh_key_filename, form.cleaned_data['pool_type'])
        
            if exit_status != 0:
                os.remove(ssh_key_filename)
    
                form._errors[NON_FIELD_ERRORS] = ErrorList(['There was an error adding the pool'] + output + errors)
                
                try:
                    log.debug('Error adding pool. Attempting to remove from bosco_cluster')
                    condor_tools.remove_bosco_pool(username+'@'+address)
                except:
                    pass
                
                return self.form_invalid(self, *args, **kwargs)
        else:
            log.debug('Adding new bosco pool %s to db, skipping bosco_cluster --add because it already exists ' % (username + '@' + address))
        
        #Assume everything went well
        os.remove(ssh_key_filename)
        
        pool = BoscoPool(name = form.cleaned_data['name'],
                         user = self.request.user,
                         platform = form.cleaned_data['platform'],
                         address = form.cleaned_data['username'] + '@' + form.cleaned_data['address'],
                         pool_type = form.cleaned_data['pool_type'],
                         status_page = form.cleaned_data['status_page_link'],
                         )
        pool.save()
                         
        return HttpResponseRedirect(reverse_lazy('pool_test', kwargs={'pool_id': pool.id}))
    

        
class PoolTestView(RestrictedView):
    page_title = 'Pool added'
    template_name = 'pool/pool_test.html'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        pool = CondorPool.objects.get(id=kwargs.get('pool_id'))
        assert pool.user == request.user
        kwargs['pool'] = pool
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Testing pool'
        kwargs['loading_description'] = 'Please do not navigate away from this page. Testing a pool can take several minutes.'

        return super(PoolTestView, self).dispatch(request, *args, **kwargs)
    
class PoolTestResultView(RestrictedView):
    
    page_title = 'Pool test result'
    template_name = 'pool/pool_test_result.html'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        pool = CondorPool.objects.get(id=kwargs.get('pool_id'))
        assert pool.user == request.user
        
        
        
        kwargs['pool'] = pool
        
        output, errors, exit_status = condor_tools.test_bosco_pool(pool.address)
        
        kwargs['output'] = output
        kwargs['stderr'] = errors
        kwargs['exit_status'] = exit_status
        
        if exit_status == 0: kwargs['success'] = True
        else: kwargs['success'] = False
        

        
        return super(PoolTestResultView, self).dispatch(request, *args, **kwargs)

class PoolRemoveView(RestrictedView):
    template_name='pool/pool_remove.html'
    page_title='Confirm pool removal'
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        pool_id = kwargs['pool_id']
        pool = CondorPool.objects.get(id=pool_id)
        

        kwargs['pool'] = pool
        kwargs['pool_type']=pool.get_pool_type()
        if kwargs['pool_type'] == 'ec2':
            kwargs['node_count'] = EC2Pool.objects.get(id=pool_id).get_count()
        confirmed= kwargs['confirmed']
        
        assert pool.user == request.user
        copied_pools = CondorPool.objects.filter(copy_of=pool)
        kwargs['copied_pools'] = copied_pools
        
        #Are there any other pools that are a copy of this one?
        pool_tasks = Task.objects.filter(condor_pool=pool) | Task.objects.filter(condor_pool__in=copied_pools)
        running_tasks = pool_tasks.filter(status='running')|pool_tasks.filter(status='new')
        other_tasks = pool_tasks.exclude(pk__in=running_tasks)
        if not confirmed:
            kwargs['show_loading_screen'] = True
            if pool.get_pool_type() == 'ec2' and pool.copy_of == None:
                kwargs['loading_title'] = 'Terminating pool'
                kwargs['loading_description'] = 'Please do not navigate away from this page. Terminating a pool can take several minutes.'
                kwargs['button_text']='Terminate pool'

            else:
                kwargs['loading_title'] = 'Removing pool'
                kwargs['loading_description'] = 'Please do not navigate away from this page. Removing a pool can take several minutes.'
                kwargs['button_text']='Remove pool'

            kwargs['running_tasks'] = running_tasks
            return super(PoolRemoveView, self).dispatch(request, *args, **kwargs)
        else:
            #Remove the pool
            
            #First, remove any running tasks
            for task in running_tasks:
                for subtask in task.subtask_set.all():
                    condor_tools.remove_task(subtask)
                task.status = 'cancelled'
                try:
                    email_tools.send_task_cancellation_email(task)
                except:
                    pass

                task.condor_pool = None
                task.set_custom_field('condor_pool_name', pool.name)
                task.save()
            #Then 'prune' the remaining tasks to remove the pool as a foreignkey
            for task in other_tasks:
                task.condor_pool = None
                task.set_custom_field('condor_pool_name', pool.name)
                task.save()
            
            
            if pool.get_pool_type() == 'ec2' and pool.copy_of == None:
                pool = EC2Pool.objects.get(id=pool.id)
                kwargs['pool'] = pool
                error_list = []
                #Remove the copied pools first
                for copied_pool in copied_pools:
                    try:
                        copied_pool.delete()
                    except Exception as e:
                        log.exception(e)
                        error_list += ['Error deleting duplicate pool', str(e)]
                #Remove from bosco
                try:
                    condor_tools.remove_ec2_pool(pool)
                except Exception as e:
                    log.exception(e)
                    error_list += ['Error removing pool from bosco', str(e)]
                
                #Terminate the pool
                errors = ec2_tools.terminate_pool(pool)
                error_list += errors
                request.session['errors']=error_list

            elif pool.get_pool_type() == 'bosco' and pool.copy_of == None:
                try:
                    #Remove any copied pools first
                    for copied_pool in copied_pools:
                        copied_pool.delete()
                    
                    #Only remove the pool from bosco if the same address is not registered with any other user
                    if CondorPool.objects.filter(address=pool.address).count() == 1:
                        condor_tools.remove_bosco_pool(pool.address)
                        log.debug('Removing pool %s from bosco' % pool.address)
                    else:
                        log.debug('Not removing pool %s from bosco, since in use by another user' % pool.address)
                    
                    #However, still delete the db entry
                    pool.delete()
                except Exception as e:
                    log.exception(e)
                    request.session['errors'] = [e]
                    return HttpResponseRedirect(reverse_lazy('pool_details', pool_id = pool.id))

                
            else:
                try:
                    pool.delete()
                except Exception as e:
                    log.exception(e)
                    request.session['errors'] = [e]
                    return HttpResponseRedirect(reverse_lazy('pool_details', pool_id = pool.id))
            
            

            
            
            return HttpResponseRedirect(reverse_lazy('pool_list'))




class SharePoolForm(forms.Form):
    username = forms.CharField(max_length=30)


class SharePoolView(RestrictedFormView):
    form_class = SharePoolForm
    template_name = 'pool/pool_share.html'
    page_title = 'Share pool'
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        
        pool = CondorPool.objects.get(id=kwargs['pool_id'])
        assert pool.user == self.request.user
        assert pool.copy_of == None


        if kwargs.get('remove'):
            unshare_from = User.objects.get(id=kwargs['user_id'])
            
            unshare_pool = CondorPool.objects.get(copy_of=pool, user=unshare_from)
            tasks = Task.objects.filter(condor_pool=unshare_pool)
            running_tasks = tasks.filter(status='running')|tasks.filter(status='new')
            for task in running_tasks:
                subtasks = task.subtask_set.all()
                for subtask in subtasks:
                    condor_tools.remove_task(subtask)
                task.delete()
            other_tasks = tasks.exclude(pk__in=running_tasks)
            #Then 'prune' the remaining tasks to remove the pool as a foreignkey
            for task in other_tasks:
                task.condor_pool = None
                task.set_custom_field('condor_pool_name', pool.name)
                task.save()
                
            
            unshare_pool.delete()
            return HttpResponseRedirect(reverse_lazy('pool_share', kwargs={'pool_id': kwargs['pool_id']}))


        shared_pools = CondorPool.objects.filter(copy_of=pool)
        
        shared_users = [pool.user for pool in shared_pools]
        
        kwargs['shared_users'] = shared_users
        
        return super(SharePoolView, self).dispatch(request, *args, **kwargs)
        
    def form_valid(self, *args, **kwargs):
        
        form = kwargs['form']
        self.success_url = reverse_lazy('pool_share', kwargs={'pool_id':kwargs['pool_id']})

        
        #Get the pool we want to share
        pool = CondorPool.objects.get(id=kwargs['pool_id'])
        assert pool.user == self.request.user
        assert pool.copy_of == None


        
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
            assert CondorPool.objects.filter(copy_of__id=pool.id, user=user).count() == 0
        except:
            form._errors[NON_FIELD_ERRORS] = ErrorList(['This pool has already been shared with that user'])
            return self.form_invalid(*args, **kwargs)

        
        #Make sure we cast the pool into the correct type
        if pool.get_pool_type() == 'ec2':
            pool = EC2Pool.objects.get(pk=pool.pk)
        else:
            pool = BoscoPool.objects.get(pk=pool.pk)
        
        copy_of = CondorPool.objects.get(pk=pool.pk)
        
        #Make a copy of the pool
        #pool.copy_of = pool
        pool.pk = None
        pool.id = None
        pool.uuid = None
        
        pool.copy_of = copy_of
        pool.user = user
        
        pool.save()
        
        
        return super(SharePoolView, self).form_valid(*args, **kwargs)

class SpotPriceHistoryForm(forms.Form):
    instance_type = forms.ChoiceField(choices=ec2_config.EC2_TYPE_CHOICES,
                                      widget=forms.widgets.Select(attrs={'style':'width:30em'}),
                                      initial='m1.medium')
    
class SpotPriceHistoryView(RestrictedView):
    template_name = 'pool/spotprice_history.html'
    page_title = 'Spot price history'
    def dispatch(self, request, *args, **kwargs):
        kwargs['form'] = SpotPriceHistoryForm()
        
        
        return super(SpotPriceHistoryView, self).dispatch(request, *args, **kwargs)
        
