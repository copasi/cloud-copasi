from django.urls import path
from web_interface import views

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



]
