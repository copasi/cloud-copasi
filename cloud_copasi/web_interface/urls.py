from django.urls import path, re_path
from web_interface import views
from web_interface.account import account_viewsN
from web_interface.pools import pool_views, task_views


# app_name = 'web_interface'

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

    path('help/terms/', views.DefaultView.as_view(),
    {'template_name':'help/termsN.html','page_title':'Help - Terms and Conditions'},
    name="help_terms"),

    # registrations
    path('register/', account_viewsN.AccountRegisterView.as_view(),
    name='my_account_register'),


    #login Logout
    path('sign_in/', views.LoginView.as_view(), name='sign_in'),
    path('sign_out/', views.LogoutView.as_view(), name='sign_out'),

    #account views
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

    #pools
    path('my_account/pools/', pool_views.PoolListView.as_view(), name = 'pool_list'),
    path('my_account/pools/add_ec2/', pool_views.EC2PoolAddView.as_view(), name='ec2_pool_add'),
    path('my_account/pools/add_existing/', pool_views.BoscoPoolAddView.as_view(), name='bosco_pool_add'),

    #Task views
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
]
