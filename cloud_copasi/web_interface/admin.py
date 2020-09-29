from django.contrib import admin
from web_interface.models import *

# Register your models here.
admin.site.register(AWSAccessKey)
admin.site.register(VPC)
admin.site.register(CondorPool)
admin.site.register(EC2Instance)
admin.site.register(EC2KeyPair)
admin.site.register(ElasticIP)
admin.site.register(Task)
admin.site.register(Subtask)
admin.site.register(CondorJob)
admin.site.register(SpotRequest)
admin.site.register(EC2Pool)
admin.site.register(BoscoPool)
admin.site.register(Profile)
