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
from cloud_copasi.web_interface.aws import task_views, pool_views
from cloud_copasi.web_interface.client_api import api_views
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', views.LandingView.as_view(), name='landing_view'),
    url(r'^home/$', views.HomeView.as_view(), name='home'),
    url(r'^about/$', views.AboutView.as_view(), name='about'),
    url(r'^my_account/$', account_views.MyAccountView.as_view(), name='my_account'),
    
    #Keys
    url(r'^my_account/keys/$', account_views.KeysView.as_view() , name='my_account_keys'),
    url(r'^my_account/keys/add/$', account_views.KeysAddView.as_view(), name='my_account_keys_add'),
    url(r'^my_account/keys/(?P<key_id>\d+)/delete$', account_views.KeysDeleteView.as_view(), {'confirmed' : False }, name='my_account_keys_delete'),
    url(r'^my_account/keys/(?P<key_id>\d+)delete/confirm/$', account_views.KeysDeleteView.as_view(),{'confirmed' : True }, name='my_account_keys_delete_confirmed'),
    
    #VPC
    url(r'^my_account/vpc_status/$', account_views.VPCStatusView.as_view(), name='vpc_status'),
    url(r'^my_account/vpc_status/(?P<key_id>\d+)/configure/$', account_views.VPCConfigView.as_view(), name='vpc_config'),
    url(r'^my_account/vpc_status/(?P<key_id>\d+)/add/$', account_views.VPCAddView.as_view(), name='vpc_add'),
    url(r'^my_account/vpc_status/(?P<key_id>\d+)/remove/$', account_views.VPCRemoveView.as_view(), name='vpc_remove'),
    
    #Pools
    url(r'^my_account/pools/$', pool_views.PoolStatusView.as_view(), name='pool_status'),
    url(r'^my_account/pools/add/$', pool_views.PoolAddView.as_view(), name='pool_add'),

    url(r'^my_account/pools/(?P<pool_id>\d+)/details/$', pool_views.PoolDetailsView.as_view(), name='pool_details'),
    url(r'^my_account/pools/(?P<pool_id>\d+)/terminate/$', pool_views.PoolTerminateView.as_view(), {'confirmed': False }, name='pool_terminate'),
    url(r'^my_account/pools/(?P<pool_id>\d+)/terminate/confirm/$', pool_views.PoolTerminateView.as_view(), {'confirmed':True}, name='pool_terminate_confirmed'),

    url(r'^my_account/change_password/$', account_views.PasswordChangeView.as_view() , name='my_account_password_change'),
    
    url(r'^sign_in/$', views.LoginView.as_view(), name='sign_in'),
    url(r'^sign_out/$', views.LogoutView.as_view(), name='sign_out'),

    
    #Task views
    url('^my_account/tasks/new/$', task_views.NewTaskView.as_view(), name='task_new'),
    url('^my_account/tasks/running/$', task_views.RunningTaskListView.as_view(), name='running_task_list'),
    url('^my_account/tasks/(?P<task_id>\d+)/details/$', task_views.TaskDetailsView.as_view(), name='task_details'),
    url('^my_account/tasks/subtask/(?P<subtask_id>\d+)/details/$', task_views.SubtaskDetailsView.as_view(), name='subtask_details'),
    url('^my_account/tasks/(?P<task_id>\d+)/delete/$', task_views.TaskDeleteView.as_view(),{'confirmed': False }, name='task_delete'),
    url('^my_account/tasks/(?P<task_id>\d+)/delete/confirm/$', task_views.TaskDeleteView.as_view(), {'confirmed': True },name='task_delete'),


    #API views for updating condor job statuses
    url(r'^api/register_job/$', api_views.RegisterJobView.as_view(), name='api_register_job'),
    url(r'^api/update_status/$', api_views.UpdateCondorStatusView.as_view(), name='api_update_status'),
    url(r'^api/register_deleted_jobs/$', api_views.RegisterDeletedJobsView.as_view(), name='api_register_deleted_jobs'),
    url(r'^api/register_transferred_files/$', api_views.RegisterTransferredFilesView.as_view(), name='api_register_transferred_files'),
    url(r'^api/remote_logging_update/$', api_views.RemoteLoggingUpdateView.as_view(), name='api_remote_logging_update'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
