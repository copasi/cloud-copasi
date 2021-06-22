from django.urls import path, re_path
from cloud_copasi.web_interface import views
from cloud_copasi.web_interface.account import account_viewsN
from cloud_copasi.web_interface.aws import resource_views
from cloud_copasi.web_interface.pools import pool_views, task_views
from cloud_copasi.web_interface.client_api import api_views

# app_name = 'web_interface'

#following imports are added on June 22, 2021
from django.contrib.auth.views import PasswordResetView, PasswordResetCompleteView, PasswordResetDoneView, PasswordResetConfirmView
from django.views.generic import RedirectView
from . import settings
from django.conf.urls.static import static
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    # path('', views.index, name='home')
    path('', views.HomeView.as_view(), name='homeN'),
    path('home/', views.HomeView.as_view(), name='homeN'),

    #Landing view
    path('', views.LandingView.as_view(), name='landing_view'),

    # Help pages
    path('help/', views.DefaultView.as_view(),
    {'template_name':'help/helpN.html', 'page_title': 'Help'},
    name='helpN'),

    path('help/contact/',views.DefaultView.as_view(),
    {'template_name':'help/contactN.html', 'page_title':'Contact Information'},
    name='contactN'),

    path('help/tasks/', views.DefaultView.as_view(),
    {'template_name':'help/tasksN.html', 'page_title':'Help - Task Submission'},
    name='help_tasks'),

    path('help/compute_pools/', views.DefaultView.as_view(),
    {'template_name':'help/poolsN.html', 'page_title':'Help - Compute Pools'},
    name='help_pools'),

    # path('help/terms/', views.DefaultView.as_view(),
    # {'template_name':'help/termsN.html','page_title':'Help - Terms and Conditions'},
    # name="help_terms"),

    path('help/terms/',
    views.DefaultView.as_view(template_name='help/termsN.html',page_title='Terms and Conditions'),
    name="help_terms"),

    # registrations
    path('register/', account_viewsN.AccountRegisterView.as_view(),
    name='my_account_register'),


    #----- login Logout
    path('sign_in/', views.LoginView.as_view(), name='sign_in'),
    path('sign_out/', views.LogoutView.as_view(), name='sign_out'),
    #-----

    #----- account views
    path('my_account/', account_viewsN.MyAccountView.as_view(), name='my_account'),
    path('my_account/profile/', account_viewsN.AccountProfileView.as_view(), name='my_account_profile'),
    path('my_account/keys/', account_viewsN.KeysView.as_view() , name='my_account_keys'),
    path('my_account/keys/add/', account_viewsN.KeysAddView.as_view(), name='my_account_keys_add'),
    re_path(r'^my_account/keys/(?P<key_id>\d+)/delete/$', account_viewsN.KeysDeleteView.as_view(), {'confirmed' : False }, name='my_account_keys_delete'),
    re_path(r'^my_account/keys/(?P<key_id>\d+)delete/confirm/$', account_viewsN.KeysDeleteView.as_view(),{'confirmed' : True }, name='my_account_keys_delete_confirmed'),
    re_path(r'^my_account/keys/(?P<key_id>\d+)/share/$', account_viewsN.KeysShareView.as_view(), name='my_account_keys_share'),
    re_path(r'^my_account/keys/(?P<key_id>\d+)/unshare/(?P<user_id>\d+)/$', account_viewsN.KeysShareView.as_view(), {'remove':True}, name='my_account_keys_unshare'),
    re_path(r'^my_account/keys/(?P<key_id>\d+)/rename/$', account_viewsN.KeysRenameView.as_view(), name='my_account_keys_rename'),

    path('my_account/change_password/', account_viewsN.PasswordChangeView.as_view() , name='my_account_password_change'),
    #-----

    #----- VPC
    re_path(r'^my_account/vpc_status/(?P<key_id>\d+)/configure/$', account_viewsN.VPCConfigView.as_view(), name='vpc_config'),
    # re_path(r'^my_account/vpc_status/(?P<key_id>\d+)/add/$', account_views.VPCAddView.as_view(), name='vpc_add'),
    #-----

    #-----  pools
    path('my_account/pools/', pool_views.PoolListView.as_view(), name = 'pool_list'),
    path('my_account/pools/add_ec2/', pool_views.EC2PoolAddView.as_view(), name='ec2_pool_add'),
    path('my_account/pools/add_existing/', pool_views.BoscoPoolAddView.as_view(), name='bosco_pool_add'),

    re_path(r'^my_account/pools/(?P<pool_id>\d+)/ec2/scale_up/$', pool_views.EC2PoolScaleUpView.as_view(), name='ec2_pool_scale_up'),
    re_path(r'^my_account/pools/(?P<pool_id>\d+)/ec2/scale_down/$', pool_views.EC2PoolScaleDownView.as_view(), name='ec2_pool_scale_down'),

    re_path(r'^my_account/pools/(?P<pool_id>\d+)/test/$', pool_views.PoolTestView.as_view(), name='pool_test'),
    re_path(r'^my_account/pools/(?P<pool_id>\d+)/test/result', pool_views.PoolTestResultView.as_view(), name='pool_test_result'),

    re_path(r'^my_account/pools/(?P<pool_id>\d+)/details/$', pool_views.PoolDetailsView.as_view(), name='pool_details'),
    re_path(r'^my_account/pools/(?P<pool_id>\d+)/remove/$', pool_views.PoolRemoveView.as_view(),{'confirmed':False}, name='pool_remove'),
    re_path(r'^my_account/pools/(?P<pool_id>\d+)/remove/comfirm/$', pool_views.PoolRemoveView.as_view(), {'confirmed':True}, name='pool_remove_confirmed'),

    re_path(r'^my_account/pools/(?P<pool_id>\d+)/share/$', pool_views.SharePoolView.as_view(), {'remove':False}, name='pool_share'),
    re_path(r'^my_account/pools/(?P<pool_id>\d+)/unshare/(?P<user_id>\d+)/$', pool_views.SharePoolView.as_view(), {'remove':True}, name='pool_unshare'),
    re_path(r'^my_account/pools/(?P<pool_id>\d+)/rename/$', pool_views.PoolRenameView.as_view(), name='pool_rename'),
    re_path(r'^my_account/pools/(?P<pool_id>\d+)/ec2/termination_settings/$', pool_views.EC2PoolTerminationSettingsView.as_view(), name='pool_termination_settings'),
    re_path(r'^my_account/pools/(?P<pool_id>\d+)/change_link/$', pool_views.BoscoPoolStatusPageView.as_view(), name='pool_link_change'),

    re_path(r'^my_account/pools/spotprice_history/$', pool_views.SpotPriceHistoryView.as_view(), name='spotprice_history'),
    #-----


    path('my_account/resource_overview/', resource_views.ResourceOverviewView.as_view(), name='resource_overview'),
    re_path(r'^my_account/resource_overview/terminate/(?P<key_id>.+)/confirmed/$', resource_views.ResourceTerminateView.as_view(), {'confirmed': True}, name='resource_terminate_confirmed'),
    re_path(r'^my_account/resource_overview/terminate/(?P<key_id>.+)/$', resource_views.ResourceTerminateView.as_view(), {'confirmed': False}, name='resource_terminate'),


    #----- Task views
    path('my_account/tasks/new/', task_views.NewTaskView.as_view(), name='task_new'),

    path('my_account/tasks/running/', task_views.TaskListView.as_view(), {'status': 'running'}, name='running_task_list'),
    path('my_account/tasks/finished/', task_views.TaskListView.as_view(), {'status': 'finished'}, name='finished_task_list'),
    path('my_account/tasks/error/', task_views.TaskListView.as_view(), {'status': 'error'}, name='error_task_list'),



    re_path('^my_account/tasks/(?P<task_id>\d+)/details/$', task_views.TaskDetailsView.as_view(), name='task_details'),
    re_path('^my_account/tasks/subtask/(?P<subtask_id>\d+)/details/$', task_views.SubtaskDetailsView.as_view(), name='subtask_details'),

    re_path('^my_account/tasks/(?P<task_id>\d+)/results/$', task_views.TaskResultView.as_view(), name='task_results'),
    re_path('^my_account/tasks/(?P<task_id>\d+)/results/download/$', task_views.TaskResultDownloadView.as_view(), name='task_results_download'),
    re_path('^my_account/tasks/(?P<task_id>\d+)/results/zip/download/$', task_views.TaskDirectoryDownloadView.as_view(), name='task_results_zip_download'),

    re_path('^my_account/tasks/(?P<task_id>\d+)/delete/$', task_views.TaskDeleteView.as_view(),{'confirmed': False }, name='task_delete'),
    re_path('^my_account/tasks/(?P<task_id>\d+)/delete/confirm/$', task_views.TaskDeleteView.as_view(), {'confirmed': True },name='task_delete_confirmed'),
    #-----

    #API views for updating condor job status_message
    #path('api/check_resource/', api_views.CheckResourceView.as_view(), name='api_check_resource'),
    re_path(r'^api/register_job/$', api_views.RegisterJobView.as_view(), name='api_register_job'),
    re_path(r'^api/update_status/$', api_views.UpdateCondorStatusView.as_view(), name='api_update_status'),
    re_path(r'^api/register_deleted_jobs/$', api_views.RegisterDeletedJobsView.as_view(), name='api_register_deleted_jobs'),
    re_path(r'^api/register_transferred_files/$', api_views.RegisterTransferredFilesView.as_view(), name='api_register_transferred_files'),
    re_path(r'^api/remote_logging_update/$', api_views.RemoteLoggingUpdateView.as_view(), name='api_remote_logging_update'),
    re_path(r'^api/check_resource/$', api_views.CheckResourceView.as_view(), name='api_check_resource'),
    re_path(r'^api/extra_task_fields/$', api_views.ExtraTaskFieldsView.as_view(), name='api_extra_task_fields'),
    re_path(r'^api/terminate_instance_alarm/$', api_views.TerminateInstanceAlarm.as_view(), name='api_terminate_instance_alarm'),
    re_path(r'^api/spot_price/$', api_views.CurrentSpotInstancePrice.as_view(), name='api_spot_price'),


]
