# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-02-25 23:33
from __future__ import unicode_literals

import cloud_copasi.web_interface.fields
import cloud_copasi.web_interface.models
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AWSAccessKey',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text=b'For your convenience, assign a unique name to this access key', max_length=100, verbose_name=b'Key name')),
                ('access_key_id', models.CharField(help_text=b'The 20-character AWS access key ID', max_length=20, validators=[django.core.validators.RegexValidator(code=b'nomatch', message=b'Length has to be 20', regex=b'^.{20}$')], verbose_name=b'Access key ID')),
                ('secret_key', models.CharField(help_text=b'The 40-character secret access key associated with the access key ID', max_length=40, validators=[django.core.validators.RegexValidator(code=b'nomatch', message=b'Length has to be 40', regex=b'^.{40}$')], verbose_name=b'Secret access key')),
                ('use_for_spotprice_history', models.BooleanField(default=False, verbose_name=b'Use this key for getting spot price history for other users')),
                ('copy_of', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.AWSAccessKey', verbose_name=b'Is this key a shared version of an original key?')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CondorJob',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('std_output_file', models.CharField(max_length=255)),
                ('log_file', models.CharField(max_length=255)),
                ('std_error_file', models.CharField(max_length=255)),
                ('job_output', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(choices=[(b'N', b'Not queued'), (b'I', b'Idle'), (b'R', b'Running'), (b'H', b'Held'), (b'F', b'Finished'), (b'D', b'Mark for deletion'), (b'U', b'Unknown'), (b'E', b'Error')], max_length=1)),
                ('process_id', models.IntegerField(blank=True, null=True)),
                ('run_time', models.FloatField(null=True)),
                ('runs', models.PositiveIntegerField(blank=True, null=True, verbose_name=b'The number of runs this particular job is performing')),
                ('copasi_file', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='CondorPool',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text=b'Choose a name for this pool', max_length=100, verbose_name=b'Pool name')),
                ('uuid', cloud_copasi.web_interface.fields.UUIDField(blank=True, editable=False, max_length=32, null=True, unique=True)),
                ('platform', models.CharField(choices=[(b'DEB6', b'Debian 6'), (b'DEB7', b'Debian 7'), (b'RH5', b'Red Hat 5'), (b'RH6', b'Red Hat 6'), (b'RH7', b'Red Hat 7'), (b'UBUNTU12', b'Ubuntu 12')], default=b'DEB6', max_length=4, verbose_name=b'The platform of the remote condor submitter we are connecting to')),
                ('address', models.CharField(blank=True, default=b'', max_length=200, verbose_name=b'The full username@remote_address of the remote submitter')),
                ('pool_type', models.CharField(choices=[(b'condor', b'Condor'), (b'pbs', b'PBS'), (b'lsf', b'LSF'), (b'sge', b'Sun Grid Engine'), (b'slurm', b'Slurm Workload Manager')], default=b'condor', max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='EC2Instance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instance_type', models.CharField(choices=[(b't1.micro', b't1.micro (<2 ECU, 1 Core, 613MB (Free tier eligible))'), (b'm1.small', b'm1.small (1 ECU, 1 Core, 1.7GB)'), (b'm1.medium', b'm1.medium (2 ECUs, 1 Core, 3.7GB)'), (b'm1.large', b'm1.large (4 ECUs, 2 Cores, 7.5GB)'), (b'm1.xlarge', b'm1.xlarge (8 ECUs, 4 Cores, 15GB)'), (b'm2.xlarge', b'm2.xlarge (6.5 ECUs, 2 Cores, 17.1GB)'), (b'm2.2xlarge', b'm2.2xlarge (13 ECUs, 4 Cores, 34.2GB)'), (b'm2.4xlarge', b'm2.4xlarge (26 ECUs, 8 Cores, 68.4GB)')], max_length=20)),
                ('instance_role', models.CharField(choices=[(b'master', b'Master'), (b'worker', b'Worker')], max_length=20)),
                ('instance_id', models.CharField(max_length=20, verbose_name=b'EC2 instance ID')),
                ('state', models.CharField(choices=[(b'pending', b'Pending'), (b'running', b'Running'), (b'shutting-down', b'Shutting down'), (b'terminated', b'Terminated'), (b'stopping', b'Stopping'), (b'stopped', b'Stopped'), (b'unknown', b'Unknown')], default=b'pending', max_length=20, verbose_name=b'Last known state')),
                ('state_transition_reason', models.CharField(blank=True, max_length=50, null=True, verbose_name=b'Why the instance changed state')),
                ('instance_status', models.CharField(default=b'initializing', max_length=20)),
                ('system_status', models.CharField(default=b'initializing', max_length=20)),
                ('termination_alarm', models.CharField(blank=True, max_length=50, null=True, verbose_name=b'The name of any attached low CPU usage termination alarm')),
            ],
        ),
        migrations.CreateModel(
            name='EC2KeyPair',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name=b'EC2 Key Pair name')),
                ('path', models.CharField(max_length=255, verbose_name=b'Location of the public key pair')),
            ],
        ),
        migrations.CreateModel(
            name='ElasticIP',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_ip', models.GenericIPAddressField()),
                ('allocation_id', models.CharField(max_length=20, verbose_name=b'The allocation ID for the IP address')),
                ('association_id', models.CharField(max_length=20, verbose_name=b'The instance association ID for the address')),
                ('instance', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.EC2Instance')),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('institution', models.CharField(max_length=50)),
                ('task_emails', models.BooleanField(default=True)),
                ('pool_emails', models.BooleanField(default=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SpotRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_id', models.CharField(max_length=20)),
                ('price', models.DecimalField(decimal_places=3, max_digits=5)),
                ('status_code', models.CharField(max_length=50)),
                ('status_message', models.CharField(max_length=500)),
                ('state', models.CharField(max_length=20)),
                ('instance_type', models.CharField(choices=[(b't1.micro', b't1.micro (<2 ECU, 1 Core, 613MB (Free tier eligible))'), (b'm1.small', b'm1.small (1 ECU, 1 Core, 1.7GB)'), (b'm1.medium', b'm1.medium (2 ECUs, 1 Core, 3.7GB)'), (b'm1.large', b'm1.large (4 ECUs, 2 Cores, 7.5GB)'), (b'm1.xlarge', b'm1.xlarge (8 ECUs, 4 Cores, 15GB)'), (b'm2.xlarge', b'm2.xlarge (6.5 ECUs, 2 Cores, 17.1GB)'), (b'm2.2xlarge', b'm2.2xlarge (13 ECUs, 4 Cores, 34.2GB)'), (b'm2.4xlarge', b'm2.4xlarge (26 ECUs, 8 Cores, 68.4GB)')], max_length=20)),
                ('ec2_instance', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.EC2Instance')),
            ],
        ),
        migrations.CreateModel(
            name='Subtask',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index', models.PositiveIntegerField(verbose_name=b'The order in this subtask is to be executed')),
                ('active', models.BooleanField(default=False)),
                ('type', models.CharField(choices=[(b'lb', b'Load balancing'), (b'main', b'Main task'), (b'process', b'Results processing'), (b'file', b'Creating file with optimal values'), (b'other', b'Other')], max_length=32)),
                ('status', models.CharField(choices=[(b'waiting', b'Waiting'), (b'ready', b'Ready'), (b'running', b'Running'), (b'finished', b'Finished'), (b'error', b'Error'), (b'delete', b'Marked for deletion'), (b'unknown', b'Unknown')], default=b'waiting', max_length=32)),
                ('cluster_id', models.IntegerField(blank=True, null=True)),
                ('spec_file', models.CharField(blank=True, max_length=255)),
                ('local', models.BooleanField(default=False, help_text=b'Is this subtask to be run locally?')),
                ('custom_fields', models.CharField(blank=True, default=b'', max_length=10000)),
                ('job_count', models.IntegerField(default=-1, help_text=b'The count of the number of condor jobs. Only set after the subtask has finished. Use get_job_count() instead to find out job count')),
                ('run_time', models.FloatField(default=-1.0, help_text=b'The cumulative run time of associated condor jobs in days. Only set after the subtask has finished. Use get_run_time() to access.')),
                ('start_time', models.DateTimeField(blank=True, help_text=b'The time this subtask started running', null=True)),
                ('finish_time', models.DateTimeField(blank=True, help_text=b'The time the subtask stopped running', null=True)),
            ],
            options={
                'ordering': ['index'],
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name=b'The name of the computing job')),
                ('submit_time', models.DateTimeField(auto_now_add=True)),
                ('finish_time', models.DateTimeField(blank=True, null=True)),
                ('last_update_time', models.DateTimeField(auto_now=True)),
                ('task_type', models.CharField(max_length=128)),
                ('original_model', models.CharField(max_length=200)),
                ('directory', models.CharField(blank=True, default=b'not_set', max_length=255)),
                ('result_view', models.BooleanField(default=True, verbose_name=b'Does this task type have a result view page?')),
                ('result_download', models.BooleanField(default=True, verbose_name=b'Does this task type have a result download page?')),
                ('custom_fields', models.CharField(blank=True, default=b'', max_length=10000)),
                ('status', models.CharField(choices=[(b'new', b'New'), (b'running', b'Running'), (b'finished', b'Finished'), (b'error', b'Error'), (b'delete', b'Deleted'), (b'cancelled', b'Cancelled'), (b'unknown', b'Unknown')], default=b'waiting', max_length=32, verbose_name=b'The status of the task')),
                ('job_count', models.IntegerField(default=-1, help_text=b'The count of the number of condor jobs. Only set after the subtask has finished. Use get_job_count() instead to find out job count')),
                ('run_time', models.FloatField(default=-1.0, help_text=b'The run time of associated condor jobs. Only set after the subtask has finished. Use get_run_time() to access.')),
            ],
        ),
        migrations.CreateModel(
            name='VPC',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vpc_id', models.CharField(max_length=20, verbose_name=b'VPC ID')),
                ('subnet_id', models.CharField(max_length=20, verbose_name=b'Subnet ID')),
                ('internet_gateway_id', models.CharField(max_length=20, verbose_name=b'Internet gateway ID')),
                ('route_table_id', models.CharField(max_length=20, verbose_name=b'Route table ID')),
                ('route_table_association_id', models.CharField(max_length=20, verbose_name=b'Route table and subnet association ID')),
                ('master_group_id', models.CharField(max_length=20, verbose_name=b'Condor Master security group ID')),
                ('worker_group_id', models.CharField(max_length=20, verbose_name=b'Condor Worker security group ID')),
                ('access_key', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.AWSAccessKey')),
            ],
        ),
        migrations.CreateModel(
            name='BoscoPool',
            fields=[
                ('condorpool_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='web_interface.CondorPool')),
                ('status_page', models.CharField(blank=True, default=b'', max_length=1000, null=True)),
            ],
            bases=('web_interface.condorpool',),
        ),
        migrations.CreateModel(
            name='EC2Pool',
            fields=[
                ('condorpool_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='web_interface.CondorPool')),
                ('size', models.PositiveIntegerField(help_text=b'The number of compute nodes to launch. In addition, a master node will also be launched.', verbose_name=b'Initial number of nodes')),
                ('initial_instance_type', models.CharField(choices=[(b't1.micro', b't1.micro (<2 ECU, 1 Core, 613MB (Free tier eligible))'), (b'm1.small', b'm1.small (1 ECU, 1 Core, 1.7GB)'), (b'm1.medium', b'm1.medium (2 ECUs, 1 Core, 3.7GB)'), (b'm1.large', b'm1.large (4 ECUs, 2 Cores, 7.5GB)'), (b'm1.xlarge', b'm1.xlarge (8 ECUs, 4 Cores, 15GB)'), (b'm2.xlarge', b'm2.xlarge (6.5 ECUs, 2 Cores, 17.1GB)'), (b'm2.2xlarge', b'm2.2xlarge (13 ECUs, 4 Cores, 34.2GB)'), (b'm2.4xlarge', b'm2.4xlarge (26 ECUs, 8 Cores, 68.4GB)')], default=b't1.micro', help_text=b'The instance type to launch. The price per hour will vary depending on the instance type. For more information on the different instance types see the <a href="">help page</a>.', max_length=20)),
                ('secret_key', models.CharField(default=cloud_copasi.web_interface.models.create_secret_key, max_length=30)),
                ('last_update_time', models.DateTimeField(auto_now_add=True)),
                ('spot_request', models.BooleanField(default=False, help_text=b'Was the pool launched with spot price bidding')),
                ('spot_price', models.DecimalField(blank=True, decimal_places=3, help_text=b'Bid price if launched with spot price bidding', max_digits=5, null=True)),
                ('auto_terminate', models.BooleanField(default=False, help_text=b'Terminate all nodes of the pool after a task has been run if no other tasks are running. Only applies after at least one task has been submitted to the pool.')),
                ('smart_terminate', models.BooleanField(default=False, help_text=b'Terminate worker nodes if they have been idle for a period of time. Note that this applies whether a task is running or not.')),
                ('alarm_notify_topic_arn', models.CharField(blank=True, max_length=80, null=True)),
                ('key_pair', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.EC2KeyPair')),
                ('master', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.EC2Instance')),
                ('vpc', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web_interface.VPC', verbose_name=b'Keypair')),
            ],
            bases=('web_interface.condorpool',),
        ),
        migrations.AddField(
            model_name='task',
            name='condor_pool',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.CondorPool'),
        ),
        migrations.AddField(
            model_name='task',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='subtask',
            name='task',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.Task'),
        ),
        migrations.AddField(
            model_name='elasticip',
            name='vpc',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web_interface.VPC'),
        ),
        migrations.AddField(
            model_name='condorpool',
            name='copy_of',
            field=models.ForeignKey(blank=True, help_text=b'Is this pool a copy of an existing pool belonging to another user?', null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.CondorPool'),
        ),
        migrations.AddField(
            model_name='condorpool',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='condorjob',
            name='subtask',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.Subtask'),
        ),
        migrations.AddField(
            model_name='spotrequest',
            name='ec2_pool',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web_interface.EC2Pool'),
        ),
        migrations.AddField(
            model_name='ec2instance',
            name='ec2_pool',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web_interface.EC2Pool'),
        ),
        migrations.AlterUniqueTogether(
            name='awsaccesskey',
            unique_together=set([('user', 'access_key_id'), ('user', 'name')]),
        ),
    ]
