#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013 Edward Kent.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------
from django.conf.urls import patterns, include, url
from cloud_copasi.web_interface import views
from cloud_copasi.web_interface.account import account_views
from cloud_copasi.web_interface.aws import resource_views
from cloud_copasi.web_interface.pools import pool_views, task_views 
from cloud_copasi.web_interface.client_api import api_views
from django.contrib.auth.views import password_reset, password_reset_complete, password_reset_done
from django.views.generic import RedirectView
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', views.LandingView.as_view(), name='landing_view'),
    url(r'^favicon\.ico$', RedirectView.as_view(url='/static/favicon.ico')),

    url(r'^home/$', views.HomeView.as_view(), name='home'),
    url(r'^my_account/$', account_views.MyAccountView.as_view(), name='my_account'),
    
    #Keys
    url(r'^my_account/keys/$', account_views.KeysView.as_view() , name='my_account_keys'),
    url(r'^my_account/keys/add/$', account_views.KeysAddView.as_view(), name='my_account_keys_add'),
    url(r'^my_account/keys/(?P<key_id>\d+)/delete/$', account_views.KeysDeleteView.as_view(), {'confirmed' : False }, name='my_account_keys_delete'),
    url(r'^my_account/keys/(?P<key_id>\d+)delete/confirm/$', account_views.KeysDeleteView.as_view(),{'confirmed' : True }, name='my_account_keys_delete_confirmed'),
    url(r'^my_account/keys/(?P<key_id>\d+)/share/$', account_views.KeysShareView.as_view(), name='my_account_keys_share'),
    url(r'^my_account/keys/(?P<key_id>\d+)/unshare/(?P<user_id>\d+)/$', account_views.KeysShareView.as_view(), {'remove':True}, name='my_account_keys_unshare'),
    url(r'^my_account/keys/(?P<key_id>\d+)/rename/$', account_views.KeysRenameView.as_view(), name='my_account_keys_rename'),

    url(r'^my_account/password/reset/$', 'django.contrib.auth.views.password_reset',
        {'post_reset_redirect' : '/my_account/password/reset/done/',
         'template_name': 'account/password_reset_form.html',
         'extra_context' : {'page_title': 'Reset password'},
         'email_template_name': 'account/password_reset_email.html',
         'subject_template_name' : 'account/password_reset_email_subject.html',
         },
        name='password_reset'),
    url(r'^my_account/password/reset/done/$', 'django.contrib.auth.views.password_reset_done',
        {'template_name': 'account/password_reset_done.html',
         'extra_context' : {'page_title': 'Reset password'},}),
    url(r'^my_account/password/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        'django.contrib.auth.views.password_reset_confirm',
        {'post_reset_redirect' : '/my_account/password/done/',
         'template_name': 'account/password_reset_confirm.html',
         'extra_context' : {'page_title': 'Reset password'},
         }),
    url(r'^my_account/password/done/$','django.contrib.auth.views.password_reset_complete',
        {'template_name': 'account/password_reset_complete.html',
         'extra_context' : {'page_title': 'Reset password'},}),
    
    
    
    url(r'^register/$', account_views.AccountRegisterView.as_view(), name='my_account_register'),


    #Help pages
    url(r'^about/$', views.AboutView.as_view(), name='about'),
    url(r'^about/terms/$', views.DefaultView.as_view(),
        {'template_name': 'about/terms.html',
         'page_title': 'Terms and conditions'}, name='terms'),


    url(r'^about/contact/$', views.DefaultView.as_view(),
        {'template_name': 'about/contact.html',
         'page_title': 'Contact information'}, name='contact'),

    #VPC
#     url(r'^my_account/vpc_status/$', account_views.VPCStatusView.as_view(), name='vpc_status'),
    url(r'^my_account/vpc_status/(?P<key_id>\d+)/configure/$', account_views.VPCConfigView.as_view(), name='vpc_config'),
#    url(r'^my_account/vpc_status/(?P<key_id>\d+)/add/$', account_views.VPCAddView.as_view(), name='vpc_add'),
#    url(r'^my_account/vpc_status/(?P<key_id>\d+)/remove/$', account_views.VPCRemoveView.as_view(), name='vpc_remove'),
    
    #Pools
    url(r'^my_account/pools/$', pool_views.PoolListView.as_view(), name='pool_list'),
    url(r'^my_account/pools/add_ec2/$', pool_views.EC2PoolAddView.as_view(), name='ec2_pool_add'),
    url(r'^my_account/pools/add_existing/$', pool_views.BoscoPoolAddView.as_view(), name='bosco_pool_add'),

    url(r'^my_account/pools/(?P<pool_id>\d+)/ec2/scale_up/$', pool_views.EC2PoolScaleUpView.as_view(), name='ec2_pool_scale_up'),
    url(r'^my_account/pools/(?P<pool_id>\d+)/ec2/scale_down/$', pool_views.EC2PoolScaleUpView.as_view(), name='ec2_pool_scale_down'),

    url(r'^my_account/pools/(?P<pool_id>\d+)/test/$', pool_views.PoolTestView.as_view(), name='pool_test'),
    url(r'^my_account/pools/(?P<pool_id>\d+)/test/result', pool_views.PoolTestResultView.as_view(), name='pool_test_result'),
    
    url(r'^my_account/pools/(?P<pool_id>\d+)/details/$', pool_views.PoolDetailsView.as_view(), name='pool_details'),
    url(r'^my_account/pools/(?P<pool_id>\d+)/remove/$', pool_views.PoolRemoveView.as_view(),{'confirmed':False}, name='pool_remove'),
    url(r'^my_account/pools/(?P<pool_id>\d+)/remove/comfirm/$', pool_views.PoolRemoveView.as_view(), {'confirmed':True}, name='pool_remove_confirmed'),

    url(r'^my_account/pools/(?P<pool_id>\d+)/share/$', pool_views.SharePoolView.as_view(), {'remove':False}, name='pool_share'),
    url(r'^my_account/pools/(?P<pool_id>\d+)/unshare/(?P<user_id>\d+)/$', pool_views.SharePoolView.as_view(), {'remove':True}, name='pool_unshare'),
    url(r'^my_account/pools/(?P<pool_id>\d+)/rename/$', pool_views.PoolRenameView.as_view(), name='pool_rename'),

    url(r'^my_account/change_password/$', account_views.PasswordChangeView.as_view() , name='my_account_password_change'),
    
    url(r'^my_account/resource_overview/$', resource_views.ResourceOverviewView.as_view(), name='resource_overview'),
    url(r'^my_account/resource_overview/terminate/(?P<key_id>.+)/confirmed/$', resource_views.ResourceTerminateView.as_view(), {'confirmed': True}, name='resource_terminate_confirmed'),
    url(r'^my_account/resource_overview/terminate/(?P<key_id>.+)/$', resource_views.ResourceTerminateView.as_view(), {'confirmed': False}, name='resource_terminate'),

    url(r'^sign_in/$', views.LoginView.as_view(), name='sign_in'),
    url(r'^sign_out/$', views.LogoutView.as_view(), name='sign_out'),

    
    #Task views
    url('^my_account/tasks/new/$', task_views.NewTaskView.as_view(), name='task_new'),
    
    url('^my_account/tasks/running/$', task_views.TaskListView.as_view(), {'status': 'running'}, name='running_task_list'),
    url('^my_account/tasks/finished/$', task_views.TaskListView.as_view(), {'status': 'finished'}, name='finished_task_list'),
    url('^my_account/tasks/error/$', task_views.TaskListView.as_view(), {'status': 'error'}, name='error_task_list'),

    
    
    url('^my_account/tasks/(?P<task_id>\d+)/details/$', task_views.TaskDetailsView.as_view(), name='task_details'),
    url('^my_account/tasks/subtask/(?P<subtask_id>\d+)/details/$', task_views.SubtaskDetailsView.as_view(), name='subtask_details'),
    
    url('^my_account/tasks/(?P<task_id>\d+)/results/$', task_views.TaskResultView.as_view(), name='task_results'),
    url('^my_account/tasks/(?P<task_id>\d+)/results/download/$', task_views.TaskResultDownloadView.as_view(), name='task_results_download'),
    url('^my_account/tasks/(?P<task_id>\d+)/results/zip/download/$', task_views.TaskDirectoryDownloadView.as_view(), name='task_results_zip_download'),

    
    
    
    url('^my_account/tasks/(?P<task_id>\d+)/delete/$', task_views.TaskDeleteView.as_view(),{'confirmed': False }, name='task_delete'),
    url('^my_account/tasks/(?P<task_id>\d+)/delete/confirm/$', task_views.TaskDeleteView.as_view(), {'confirmed': True },name='task_delete_confirmed'),


    #API views for updating condor job statuses
    url(r'^api/register_job/$', api_views.RegisterJobView.as_view(), name='api_register_job'),
    url(r'^api/update_status/$', api_views.UpdateCondorStatusView.as_view(), name='api_update_status'),
    url(r'^api/register_deleted_jobs/$', api_views.RegisterDeletedJobsView.as_view(), name='api_register_deleted_jobs'),
    url(r'^api/register_transferred_files/$', api_views.RegisterTransferredFilesView.as_view(), name='api_register_transferred_files'),
    url(r'^api/remote_logging_update/$', api_views.RemoteLoggingUpdateView.as_view(), name='api_remote_logging_update'),
    url(r'^api/check_resource/$', api_views.CheckResourceView.as_view(), name='api_check_resource'),
    url(r'^api/extra_task_fields/$', api_views.ExtraTaskFieldsView.as_view(), name='api_extra_task_fields'),
    url(r'^api/terminate_instance_alarm/$', api_views.TerminateInstanceAlarm.as_view(), name='api_terminate_instance_alarm'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
