"""cloud_copasi URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from web_interface import views
from web_interface.account import account_viewsN
#from cloud_copasi.web_interface.aws import resource_views
#from cloud_copasi.web_interface.pools import pool_views, task_views
#from cloud_copasi.web_interface.client_api import api_views

#from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView,\
#    PasswordResetCompleteView, PasswordResetConfirmView
#from django.views.generic import RedirectView
#from . import settings
#from django.conf.urls.static import static
from django.contrib import admin
#admin.autodiscover()

urlpatterns = [
    #path('home/', views.HomeView.as_view(), name='home'),
    # path('', views.index, name = 'index'),
    # path('home/', include('web_interface.urls')),
    path('', include('web_interface.urls')),
    path('admin/', admin.site.urls),
]
