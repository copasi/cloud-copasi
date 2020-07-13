from django.urls import path
from web_interface import views
from web_interface.account import account_viewsN

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
    


]
