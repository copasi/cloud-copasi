from django.urls import path
from web_interface import views

# app_name = 'web_interface'

urlpatterns = [
    # path('', views.index, name='home')
    path('', views.HomeView.as_view(), name='homeN'),
    path('home/', views.HomeView.as_view(), name='homeN'),

    # Help pages
    path('help/', views.DefaultView.as_view(),
    {'template_name':'help/help.html', 'page_title': 'Help'},
    name='help'),
]
