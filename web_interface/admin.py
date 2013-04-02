from django.contrib import admin
from web_interface.models import AWSAccessKey, VPC, CondorPool, EC2Instance, AMI, EC2KeyPair, ElasticIP

admin.site.register(AWSAccessKey)
admin.site.register(VPC)
admin.site.register(CondorPool)
admin.site.register(EC2Instance)
admin.site.register(AMI)
admin.site.register(EC2KeyPair)
admin.site.register(ElasticIP)