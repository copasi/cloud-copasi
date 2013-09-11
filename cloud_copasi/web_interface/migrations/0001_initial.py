# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Profile'
        db.create_table(u'web_interface_profile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('institution', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'web_interface', ['Profile'])

        # Adding model 'AWSAccessKey'
        db.create_table(u'web_interface_awsaccesskey', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('access_key_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('secret_key', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('copy_of', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web_interface.AWSAccessKey'], null=True, blank=True)),
        ))
        db.send_create_signal('web_interface', ['AWSAccessKey'])

        # Adding unique constraint on 'AWSAccessKey', fields ['user', 'name']
        db.create_unique(u'web_interface_awsaccesskey', ['user_id', 'name'])

        # Adding unique constraint on 'AWSAccessKey', fields ['user', 'access_key_id']
        db.create_unique(u'web_interface_awsaccesskey', ['user_id', 'access_key_id'])

        # Adding model 'VPC'
        db.create_table(u'web_interface_vpc', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('access_key', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['web_interface.AWSAccessKey'], unique=True, null=True)),
            ('vpc_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('subnet_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('internet_gateway_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('route_table_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('route_table_association_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('master_group_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('worker_group_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('s3_bucket_name', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal('web_interface', ['VPC'])

        # Adding model 'CondorPool'
        db.create_table(u'web_interface_condorpool', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('uuid', self.gf('cloud_copasi.web_interface.fields.UUIDField')(max_length=32, unique=True, null=True, blank=True)),
            ('copy_of', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web_interface.CondorPool'], null=True, blank=True)),
            ('platform', self.gf('django.db.models.fields.CharField')(default='DEB6', max_length=4)),
            ('address', self.gf('django.db.models.fields.CharField')(default='', max_length=200, blank=True)),
            ('pool_type', self.gf('django.db.models.fields.CharField')(default='condor', max_length=20)),
        ))
        db.send_create_signal('web_interface', ['CondorPool'])

        # Adding model 'BoscoPool'
        db.create_table(u'web_interface_boscopool', (
            (u'condorpool_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['web_interface.CondorPool'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('web_interface', ['BoscoPool'])

        # Adding model 'EC2Pool'
        db.create_table(u'web_interface_ec2pool', (
            (u'condorpool_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['web_interface.CondorPool'], unique=True, primary_key=True)),
            ('vpc', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web_interface.VPC'])),
            ('master', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web_interface.EC2Instance'], null=True)),
            ('size', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('key_pair', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web_interface.EC2KeyPair'], null=True)),
            ('initial_instance_type', self.gf('django.db.models.fields.CharField')(default='t1.micro', max_length=20)),
            ('secret_key', self.gf('django.db.models.fields.CharField')(default='IRm4g360dhGIvBNrnVU7GKmN6L3gMB', max_length=30)),
            ('last_update_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('auto_terminate', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('alarm_notify_topic_arn', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
        ))
        db.send_create_signal('web_interface', ['EC2Pool'])

        # Adding model 'EC2Instance'
        db.create_table(u'web_interface_ec2instance', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ec2_pool', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web_interface.EC2Pool'])),
            ('instance_type', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('instance_role', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('instance_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('state', self.gf('django.db.models.fields.CharField')(default='pending', max_length=20)),
            ('state_transition_reason', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('instance_status', self.gf('django.db.models.fields.CharField')(default='initializing', max_length=20)),
            ('system_status', self.gf('django.db.models.fields.CharField')(default='initializing', max_length=20)),
            ('termination_alarm', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
        ))
        db.send_create_signal('web_interface', ['EC2Instance'])

        # Adding model 'SpotRequest'
        db.create_table(u'web_interface_spotrequest', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ec2_pool', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web_interface.EC2Pool'])),
            ('ec2_instance', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web_interface.EC2Instance'], null=True)),
            ('request_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('max_price', self.gf('django.db.models.fields.FloatField')()),
            ('status_code', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('status_message', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal('web_interface', ['SpotRequest'])

        # Adding model 'AMI'
        db.create_table(u'web_interface_ami', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('owner', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('image_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('web_interface', ['AMI'])

        # Adding model 'EC2KeyPair'
        db.create_table(u'web_interface_ec2keypair', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('path', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('web_interface', ['EC2KeyPair'])

        # Adding model 'ElasticIP'
        db.create_table(u'web_interface_elasticip', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('public_ip', self.gf('django.db.models.fields.IPAddressField')(max_length=15)),
            ('instance', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['web_interface.EC2Instance'], unique=True, null=True)),
            ('vpc', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web_interface.VPC'])),
            ('allocation_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('association_id', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal('web_interface', ['ElasticIP'])

        # Adding model 'Task'
        db.create_table(u'web_interface_task', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('condor_pool', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web_interface.CondorPool'], null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('submit_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('finish_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('last_update_time', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('task_type', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('original_model', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('directory', self.gf('django.db.models.fields.CharField')(default='not_set', max_length=255, blank=True)),
            ('result_view', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('result_download', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('custom_fields', self.gf('django.db.models.fields.CharField')(default='', max_length=10000, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default='waiting', max_length=32)),
            ('job_count', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('run_time', self.gf('django.db.models.fields.FloatField')(default=-1.0)),
        ))
        db.send_create_signal('web_interface', ['Task'])

        # Adding model 'Subtask'
        db.create_table(u'web_interface_subtask', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('task', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web_interface.Task'], null=True)),
            ('index', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('status', self.gf('django.db.models.fields.CharField')(default='waiting', max_length=32)),
            ('cluster_id', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('spec_file', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('local', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('custom_fields', self.gf('django.db.models.fields.CharField')(default='', max_length=10000, blank=True)),
            ('job_count', self.gf('django.db.models.fields.IntegerField')(default=-1)),
            ('run_time', self.gf('django.db.models.fields.FloatField')(default=-1.0)),
            ('start_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('finish_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'web_interface', ['Subtask'])

        # Adding model 'CondorJob'
        db.create_table(u'web_interface_condorjob', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subtask', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web_interface.Subtask'], null=True)),
            ('std_output_file', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('log_file', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('std_error_file', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('job_output', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('process_id', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('run_time', self.gf('django.db.models.fields.FloatField')(null=True)),
            ('runs', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('copasi_file', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('web_interface', ['CondorJob'])


    def backwards(self, orm):
        # Removing unique constraint on 'AWSAccessKey', fields ['user', 'access_key_id']
        db.delete_unique(u'web_interface_awsaccesskey', ['user_id', 'access_key_id'])

        # Removing unique constraint on 'AWSAccessKey', fields ['user', 'name']
        db.delete_unique(u'web_interface_awsaccesskey', ['user_id', 'name'])

        # Deleting model 'Profile'
        db.delete_table(u'web_interface_profile')

        # Deleting model 'AWSAccessKey'
        db.delete_table(u'web_interface_awsaccesskey')

        # Deleting model 'VPC'
        db.delete_table(u'web_interface_vpc')

        # Deleting model 'CondorPool'
        db.delete_table(u'web_interface_condorpool')

        # Deleting model 'BoscoPool'
        db.delete_table(u'web_interface_boscopool')

        # Deleting model 'EC2Pool'
        db.delete_table(u'web_interface_ec2pool')

        # Deleting model 'EC2Instance'
        db.delete_table(u'web_interface_ec2instance')

        # Deleting model 'SpotRequest'
        db.delete_table(u'web_interface_spotrequest')

        # Deleting model 'AMI'
        db.delete_table(u'web_interface_ami')

        # Deleting model 'EC2KeyPair'
        db.delete_table(u'web_interface_ec2keypair')

        # Deleting model 'ElasticIP'
        db.delete_table(u'web_interface_elasticip')

        # Deleting model 'Task'
        db.delete_table(u'web_interface_task')

        # Deleting model 'Subtask'
        db.delete_table(u'web_interface_subtask')

        # Deleting model 'CondorJob'
        db.delete_table(u'web_interface_condorjob')


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
            'secret_key': ('django.db.models.fields.CharField', [], {'default': "'TNxnpclFYnETlwkoIf4nVqBwdBvIaC'", 'max_length': '30'}),
            'size': ('django.db.models.fields.PositiveIntegerField', [], {}),
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
            'max_price': ('django.db.models.fields.FloatField', [], {}),
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
            's3_bucket_name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'subnet_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'vpc_id': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'worker_group_id': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        }
    }

    complete_apps = ['web_interface']