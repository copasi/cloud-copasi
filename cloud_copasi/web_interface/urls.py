from django.urls import path
from web_interface import views

# app_name = 'web_interface'

urlpatterns = [
    # path('', views.index, name='home')
    path('', views.HomeView.as_view(), name='home1')
]
