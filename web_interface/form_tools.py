#-------------------------------------------------------------------------------
# Cloud-COPASI
# Copyright (c) 2013-2022 Edward Kent, Hasan Baig.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from django import forms
from django.db import models


# Subclass the modelchoicefield so that we can just use the display name of the object
class NameChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "%s" % (obj.name)


# Subclass the modelchoicefield so that we can just use the display name of the object
class PoolChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if hasattr(obj, 'ec2pool'):
            pool_type = 'EC2'
        elif hasattr(obj, 'boscopool'):
            pool_type = str(obj.boscopool.get_pool_type_display())
        else:
            pool_type = 'Unknown'

        if obj.copy_of != None:
            return "%s (%s) (Shared)" % (obj.name, pool_type)
        else:
            return "%s (%s)" % (obj.name, pool_type)


# Generic function for saving a django UploadedFile to a destination
def handle_uploaded_file(f,destination):
    destination = open(destination, 'wb+')
    for chunk in f.chunks():
        destination.write(chunk)
    destination.close()
