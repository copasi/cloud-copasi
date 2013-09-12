# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'SpotRequest.max_price'
        db.delete_column(u'web_interface_spotrequest', 'max_price')

        # Adding field 'SpotRequest.price'
        db.add_column(u'web_interface_spotrequest', 'price',
                      self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=5, decimal_places=3),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'SpotRequest.max_price'
        db.add_column(u'web_interface_spotrequest', 'max_price',
                      self.gf('django.db.models.fields.FloatField')(default=0),
                      keep_default=False)

        # Deleting field 'SpotRequest.price'
        db.delete_column(u'web_interface_spotrequest', 'price')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'web_interface.ami': {
            'Meta': {'object_name': 'AMI'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'owner': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'})
        },
        'web_interface.awsaccesskey': {
            'Meta': {'unique_together': "(('user', 'name'), ('user', 'access_key_id'))", 'object_name': 'AWSAccessKey'},
            'access_key_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'copy_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web_interface.AWSAccessKey']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'secret_key': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        'web_interface.boscopool': {
            'Meta': {'object_name': 'BoscoPool', '_ormbases': ['web_interface.CondorPool']},
            u'condorpool_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['web_interface.CondorPool']", 'unique': 'True', 'primary_key': 'True'})
        },
        'web_interface.condorjob': {
            'Meta': {'object_name': 'CondorJob'},
            'copasi_file': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job_output': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'log_file': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'process_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'run_time': ('django.db.models.fields.FloatField', [], {'null': 'True'}),
            'runs': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'std_error_file': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'std_output_file': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subtask': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['web_interface.Subtask']", 'null': 'True'})
        },
        'web_interface.condorpool': {
            'Meta': {'object_name': 'CondorPool'},
            'address': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'copy_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web_interface.CondorPool']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'platform': ('django.db.models.fields.CharField', [], {'default': "'DEB6'", 'max_length': '4'}),
            'pool_type': ('django.db.models.fields.CharField', [], {'default': "'condor'", 'max_length': '20'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'uuid': ('cloud_copasi.web_interface.fields.UUIDField', [], {'max_length': '32', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        'web_interface.ec2instance': {
            'Meta': {'object_name': 'EC2Instance'},
            'ec2_pool': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web_interface.EC2Pool']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'instance_role': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'instance_status': ('django.db.models.fields.CharField', [], {'default': "'initializing'", 'max_length': '20'}),
            'instance_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '20'}),
            'state_transition_reason': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'system_status': ('django.db.models.fields.CharField', [], {'default': "'initializing'", 'max_length': '20'}),
            'termination_alarm': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'})
        },
        'web_interface.ec2keypair': {
            'Meta': {'object_name': 'EC2KeyPair'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'web_interface.ec2pool': {
            'Meta': {'object_name': 'EC2Pool', '_ormbases': ['web_interface.CondorPool']},
            'alarm_notify_topic_arn': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'auto_terminate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'condorpool_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['web_interface.CondorPool']", 'unique': 'True', 'primary_key': 'True'}),
            'initial_instance_type': ('django.db.models.fields.CharField', [], {'default': "'t1.micro'", 'max_length': '20'}),
            'key_pair': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web_interface.EC2KeyPair']", 'null': 'True'}),
            'last_update_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'master': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web_interface.EC2Instance']", 'null': 'True'}),
            'secret_key': ('django.db.models.fields.CharField', [], {'default': "'FcotYvIKdcjGynxzIggL3TonzkRXPg'", 'max_length': '30'}),
            'size': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'spot_price': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '3', 'blank': 'True'}),
            'spot_request': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'vpc': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web_interface.VPC']"})
        },
        'web_interface.elasticip': {
            'Meta': {'object_name': 'ElasticIP'},
            'allocation_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'association_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['web_interface.EC2Instance']", 'unique': 'True', 'null': 'True'}),
            'public_ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'vpc': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web_interface.VPC']"})
        },
        u'web_interface.profile': {
            'Meta': {'object_name': 'Profile'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        'web_interface.spotrequest': {
            'Meta': {'object_name': 'SpotRequest'},
            'ec2_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web_interface.EC2Instance']", 'null': 'True'}),
            'ec2_pool': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web_interface.EC2Pool']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '3'}),
            'request_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'status_code': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'status_message': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        u'web_interface.subtask': {
            'Meta': {'object_name': 'Subtask'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cluster_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'custom_fields': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10000', 'blank': 'True'}),
            'finish_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'job_count': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'local': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'run_time': ('django.db.models.fields.FloatField', [], {'default': '-1.0'}),
            'spec_file': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'waiting'", 'max_length': '32'}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web_interface.Task']", 'null': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'web_interface.task': {
            'Meta': {'object_name': 'Task'},
            'condor_pool': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web_interface.CondorPool']", 'null': 'True', 'blank': 'True'}),
            'custom_fields': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '10000', 'blank': 'True'}),
            'directory': ('django.db.models.fields.CharField', [], {'default': "'not_set'", 'max_length': '255', 'blank': 'True'}),
            'finish_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job_count': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'last_update_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'original_model': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'result_download': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'result_view': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'run_time': ('django.db.models.fields.FloatField', [], {'default': '-1.0'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'waiting'", 'max_length': '32'}),
            'submit_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'task_type': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        'web_interface.vpc': {
            'Meta': {'object_name': 'VPC'},
            'access_key': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['web_interface.AWSAccessKey']", 'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'internet_gateway_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'master_group_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'route_table_association_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'route_table_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'subnet_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'vpc_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'worker_group_id': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        }
    }

    complete_apps = ['web_interface']