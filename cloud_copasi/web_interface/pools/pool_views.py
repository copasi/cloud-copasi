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
from cloud_copasi.web_interface.pools import condor_tools
from cloud_copasi.web_interface import models
from boto.exception import EC2ResponseError, BotoServerError
from cloud_copasi.web_interface.models import VPC
import logging
import tempfile, subprocess
from django.core.validators import RegexValidator
import os
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.util import ErrorList
from django.http.response import HttpResponseRedirect
from django.contrib.auth.models import User

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
    def form_valid(self, *args, **kwargs):
        
        form = kwargs['form']
        pool = CondorPool.objects.get(id=kwargs['pool_id'])
        
        self.success_url = reverse_lazy('pool_details', kwargs={'pool_id': kwargs['pool_id']})
        return super(PoolRenameView, self).form_valid(*args, **kwargs)


    
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
    success_url = reverse_lazy('pool_list')
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
            pool.save()
            
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
        
        #Connect to Bosco
        condor_tools.add_ec2_pool(pool)
        
        #except Exception, e:
        #    self.request.session['errors'] = aws_tools.process_errors([e])
        #    return HttpResponseRedirect(reverse_lazy('pool_add'))
        
        self.success_url = reverse_lazy('pool_test', kwargs={'pool_id':pool.id})
        
        return super(EC2PoolAddView, self).form_valid(*args, **kwargs)

    def dispatch(self, *args, **kwargs):
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Launching pool'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. Launching a pool can take several minutes'

        return super(EC2PoolAddView, self).dispatch(*args, **kwargs)

    
class PoolDetailsView(RestrictedView):
    template_name='pool/pool_details.html'
    page_title = 'Pool details'
        
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        
        pool = CondorPool.objects.get(id=kwargs['pool_id'])
        kwargs['pool'] = pool
        
        assert isinstance(pool, CondorPool)
        assert pool.user == self.request.user
        
        if pool.copy_of != None:
            pool_type = 'shared'
            original_pool = pool.copy_of
        elif pool.get_pool_type() == 'ec2':
            pool_type = 'ec2'
        else:
            pool_type = 'bosco'
            
        kwargs['pool_type'] = pool_type
        
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

            try:
                assert pool.vpc.access_key.user == request.user
                ec2_tools.refresh_pool(pool)
            except EC2ResponseError, e:
                request.session['errors'] = [error for error in e.errors]
                log.exception(e)
                return HttpResponseRedirect(reverse_lazy('pool_list'))
            except Exception, e:
                self.request.session['errors'] = [e]
                log.exception(e)
                return HttpResponseRedirect(reverse_lazy('pool_list'))
            
            instances=EC2Instance.objects.filter(ec2_pool=pool)
            
            try:
                master_id = pool.master.id
            except:
                master_id=None
            
            compute_instances = instances.exclude(id=master_id)
            
            kwargs['instances'] = instances
            kwargs['compute_instances'] = compute_instances

        else:
            #Pool type is bosco
            pass
        
        
        
        
        #Text for pool test screen
        kwargs['show_loading_screen'] = True
        kwargs['loading_title'] = 'Testing pool'
        kwargs['loading_description'] = 'Please be patient and do not navigate away from this page. Testing a pool can take several minutes.'

        
        return super(PoolDetailsView, self).dispatch(request, *args, **kwargs)

    
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
    success_url = reverse_lazy('pool_list')
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
            return HttpResponseRedirect(reverse_lazy('pool_list'))

        
        
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
    
    address = forms.CharField(max_length=200,
                              help_text='The address or IP of the remote submit node (e.g. server.campus.edu or 86.3.3.2)',
                              validators=[RegexValidator(r'^[a-z0-9-.]+(:([0-9]+)){0,1}$')])
    
    username = forms.CharField(max_length=50, help_text='The username used to log in to the remote submit node',
                               validators=[RegexValidator(r'^[A-Za-z0-9]+(?:[_-][A-Za-z0-9]+)*$')])
    
    pool_type = forms.ChoiceField(choices = (
                                                           ('condor', 'Condor'),
                                                           ('pbs', 'PBS'),
                                                           ('lsf', 'LSF'),
                                                           ('sge', 'Sun Grid Engine'),
                                                           ),
                                 initial='condor',
                                 )
    
    platform = forms.ChoiceField(label='Remote platform',
                                 help_text='The platform of the remote submitter we are connecting to. Not sure which to select? See the documentation for full details.',
                                choices = (
                                           ('DEB6', 'Debian 6'),
                                           ('RH5', 'Red Hat 5'),
                                           ('RH6', 'Red Hat 6'),
                                           ),
                                initial='DEB6',
                                )

    ssh_key = forms.CharField(max_length = 10000,
                              label = 'SSH private key',
                              help_text = 'A working SSH private key for the pool submit node. This key will used only once, and will not be stored. See the documentation for full details on how to generate this.',
                              widget=forms.Textarea)

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
        
        confirmed= kwargs['confirmed']
        
        assert pool.user == request.user
        copied_pools = CondorPool.objects.filter(copy_of=pool)
        
        
        #Are there any other pools that are a copy of this one?
                
        if not confirmed:
            kwargs['show_loading_screen'] = True
            if pool.get_pool_type() == 'ec2' and pool.copy_of == None:
                kwargs['loading_title'] = 'Terminating pool'
                kwargs['loading_description'] = 'Please do not navigate away from this page. Terminating a pool can take several minutes.'
            else:
                kwargs['loading_title'] = 'Removing pool'
                kwargs['loading_description'] = 'Please do not navigate away from this page. Removing a pool can take several minutes.'


            return super(PoolRemoveView, self).dispatch(request, *args, **kwargs)
        else:
            #Remove the pool
            
            if pool.get_pool_type() == 'ec2' and pool.copy_of == None:
                pool = EC2Pool.objects.get(id=pool.id)
                kwargs['pool'] = pool
                
                error_list = []
                #Remove the copied pools first
                for copied_pool in copied_pools:
                    try:
                        copied_pool.delete()
                    except Exception, e:
                        log.exception(e)
                        error_list += ['Error deleting duplicate pool', str(e)]
                #Remove from bosco
                try:
                    condor_tools.remove_ec2_pool(pool)
                except Exception, e:
                    log.exception(e)
                    error_list += ['Error removing pool from bosco', str(e)]
                
                #Terminate the pool
                errors = ec2_tools.terminate_pool(pool)
                error_list += errors
                request.session['errors']=error_list

            elif pool.get_pool_type == 'bosco' and pool.copy_of == None:
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
                except Exception, e:
                    log.exception(e)
                    request.session['errors'] = [e]
                    return HttpResponseRedirect(reverse_lazy('pool_details', pool_id = pool.id))

                
            else:
                #TODO
                try:
                    pool.delete()
                except Exception, e:
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
