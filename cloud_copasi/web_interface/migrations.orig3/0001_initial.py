# Generated by Django 3.1.5 on 2021-04-01 14:45

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
                ('name', models.CharField(help_text='For your convenience, assign a unique name to this access key', max_length=100, verbose_name='Key name')),
                ('access_key_id', models.CharField(help_text='The 20-character AWS access key ID', max_length=20, validators=[django.core.validators.RegexValidator(code='nomatch', message='Length has to be 20', regex='^.{20}$')], verbose_name='Access key ID')),
                ('secret_key', models.CharField(help_text='The 40-character secret access key associated with the access key ID', max_length=40, validators=[django.core.validators.RegexValidator(code='nomatch', message='Length has to be 40', regex='^.{40}$')], verbose_name='Secret access key')),
                ('use_for_spotprice_history', models.BooleanField(default=False, verbose_name='Use this key for getting spot price history for other users')),
                ('copy_of', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.awsaccesskey', verbose_name='Is this key a shared version of an original key?')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'name'), ('user', 'access_key_id')},
            },
        ),
        migrations.CreateModel(
            name='CondorPool',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Choose a name for this pool', max_length=100, verbose_name='Pool name')),
                ('uuid', cloud_copasi.web_interface.fields.UUIDField(blank=True, editable=False, max_length=32, null=True, unique=True)),
                ('platform', models.CharField(choices=[('DEB6', 'Debian 6'), ('DEB7', 'Debian 7'), ('RH5', 'Red Hat 5'), ('RH6', 'Red Hat 6'), ('RH7', 'Red Hat 7'), ('UBUNTU12', 'Ubuntu 12'), ('MACOS', 'MAC OS')], default='DEB6', max_length=8, verbose_name='The platform of the remote condor submitter we are connecting to')),
                ('address', models.CharField(blank=True, default='', max_length=200, verbose_name='The full username@remote_address of the remote submitter')),
                ('pool_type', models.CharField(choices=[('condor', 'Condor'), ('pbs', 'PBS'), ('lsf', 'LSF'), ('sge', 'Sun Grid Engine'), ('slurm', 'Slurm Workload Manager')], default='condor', max_length=20)),
                ('copy_of', models.ForeignKey(blank=True, help_text='Is this pool a copy of an existing pool belonging to another user?', null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.condorpool')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='EC2Instance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instance_type', models.CharField(choices=[('t1.micro', 't1.micro (<2 ECU, 1 Core, 613MB (Free tier eligible))'), ('m1.small', 'm1.small (1 ECU, 1 Core, 1.7GB)'), ('m1.medium', 'm1.medium (2 ECUs, 1 Core, 3.7GB)'), ('m1.large', 'm1.large (4 ECUs, 2 Cores, 7.5GB)'), ('m1.xlarge', 'm1.xlarge (8 ECUs, 4 Cores, 15GB)'), ('m2.xlarge', 'm2.xlarge (6.5 ECUs, 2 Cores, 17.1GB)'), ('m2.2xlarge', 'm2.2xlarge (13 ECUs, 4 Cores, 34.2GB)'), ('m2.4xlarge', 'm2.4xlarge (26 ECUs, 8 Cores, 68.4GB)')], max_length=20)),
                ('instance_role', models.CharField(choices=[('master', 'Master'), ('worker', 'Worker')], max_length=20)),
                ('instance_id', models.CharField(max_length=20, verbose_name='EC2 instance ID')),
                ('state', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('shutting-down', 'Shutting down'), ('terminated', 'Terminated'), ('stopping', 'Stopping'), ('stopped', 'Stopped'), ('unknown', 'Unknown')], default='pending', max_length=20, verbose_name='Last known state')),
                ('state_transition_reason', models.CharField(blank=True, max_length=50, null=True, verbose_name='Why the instance changed state')),
                ('instance_status', models.CharField(default='initializing', max_length=20)),
                ('system_status', models.CharField(default='initializing', max_length=20)),
                ('termination_alarm', models.CharField(blank=True, max_length=50, null=True, verbose_name='The name of any attached low CPU usage termination alarm')),
            ],
        ),
        migrations.CreateModel(
            name='EC2KeyPair',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='EC2 Key Pair name')),
                ('path', models.CharField(max_length=255, verbose_name='Location of the public key pair')),
            ],
        ),
        migrations.CreateModel(
            name='BoscoPool',
            fields=[
                ('condorpool_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='web_interface.condorpool')),
                ('status_page', models.CharField(blank=True, default='', max_length=1000, null=True)),
            ],
            bases=('web_interface.condorpool',),
        ),
        migrations.CreateModel(
            name='EC2Pool',
            fields=[
                ('condorpool_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='web_interface.condorpool')),
                ('size', models.PositiveIntegerField(help_text='The number of compute nodes to launch. In addition, a master node will also be launched.', verbose_name='Initial number of nodes')),
                ('initial_instance_type', models.CharField(choices=[('t1.micro', 't1.micro (<2 ECU, 1 Core, 613MB (Free tier eligible))'), ('m1.small', 'm1.small (1 ECU, 1 Core, 1.7GB)'), ('m1.medium', 'm1.medium (2 ECUs, 1 Core, 3.7GB)'), ('m1.large', 'm1.large (4 ECUs, 2 Cores, 7.5GB)'), ('m1.xlarge', 'm1.xlarge (8 ECUs, 4 Cores, 15GB)'), ('m2.xlarge', 'm2.xlarge (6.5 ECUs, 2 Cores, 17.1GB)'), ('m2.2xlarge', 'm2.2xlarge (13 ECUs, 4 Cores, 34.2GB)'), ('m2.4xlarge', 'm2.4xlarge (26 ECUs, 8 Cores, 68.4GB)')], default='t1.micro', help_text='The instance type to launch. The price per hour will vary depending on the instance type. For more information on the different instance types see the <a href="">help page</a>.', max_length=20)),
                ('secret_key', models.CharField(default=cloud_copasi.web_interface.models.create_secret_key, max_length=30)),
                ('last_update_time', models.DateTimeField(auto_now_add=True)),
                ('spot_request', models.BooleanField(default=False, help_text='Was the pool launched with spot price bidding')),
                ('spot_price', models.DecimalField(blank=True, decimal_places=3, help_text='Bid price if launched with spot price bidding', max_digits=5, null=True)),
                ('auto_terminate', models.BooleanField(default=False, help_text='Terminate all nodes of the pool after a task has been run if no other tasks are running. Only applies after at least one task has been submitted to the pool.')),
                ('smart_terminate', models.BooleanField(default=False, help_text='Terminate worker nodes if they have been idle for a period of time. Note that this applies whether a task is running or not.')),
                ('alarm_notify_topic_arn', models.CharField(blank=True, max_length=80, null=True)),
                ('key_pair', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.ec2keypair')),
                ('master', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.ec2instance')),
            ],
            bases=('web_interface.condorpool',),
        ),
        migrations.CreateModel(
            name='VPC',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vpc_id', models.CharField(max_length=20, verbose_name='VPC ID')),
                ('subnet_id', models.CharField(max_length=20, verbose_name='Subnet ID')),
                ('internet_gateway_id', models.CharField(max_length=20, verbose_name='Internet gateway ID')),
                ('route_table_id', models.CharField(max_length=20, verbose_name='Route table ID')),
                ('route_table_association_id', models.CharField(max_length=20, verbose_name='Route table and subnet association ID')),
                ('master_group_id', models.CharField(max_length=20, verbose_name='Condor Master security group ID')),
                ('worker_group_id', models.CharField(max_length=20, verbose_name='Condor Worker security group ID')),
                ('access_key', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.awsaccesskey')),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='The name of the computing job')),
                ('submit_time', models.DateTimeField(auto_now_add=True)),
                ('finish_time', models.DateTimeField(blank=True, null=True)),
                ('last_update_time', models.DateTimeField(auto_now=True)),
                ('task_type', models.CharField(max_length=128)),
                ('original_model', models.CharField(max_length=200)),
                ('directory', models.CharField(blank=True, default='not_set', max_length=255)),
                ('result_view', models.BooleanField(blank=True, default=True, verbose_name='Does this task type have a result view page?')),
                ('result_download', models.BooleanField(blank=True, default=True, verbose_name='Does this task type have a result download page?')),
                ('custom_fields', models.CharField(blank=True, default='', max_length=10000)),
                ('status', models.CharField(choices=[('new', 'New'), ('running', 'Running'), ('finished', 'Finished'), ('error', 'Error'), ('delete', 'Deleted'), ('cancelled', 'Cancelled'), ('unknown', 'Unknown')], default='waiting', max_length=32, verbose_name='The status of the task')),
                ('job_count', models.IntegerField(default=-1, help_text='The count of the number of condor jobs. Only set after the subtask has finished. Use get_job_count() instead to find out job count')),
                ('run_time', models.FloatField(default=-1.0, help_text='The run time of associated condor jobs. Only set after the subtask has finished. Use get_run_time() to access.')),
                ('condor_pool', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.condorpool')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Subtask',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index', models.PositiveIntegerField(verbose_name='The order in this subtask is to be executed')),
                ('active', models.BooleanField(default=False)),
                ('type', models.CharField(choices=[('lb', 'Load balancing'), ('main', 'Main task'), ('process', 'Results processing'), ('file', 'Creating file with optimal values'), ('other', 'Other')], max_length=32)),
                ('status', models.CharField(choices=[('waiting', 'Waiting'), ('ready', 'Ready'), ('running', 'Running'), ('finished', 'Finished'), ('error', 'Error'), ('delete', 'Marked for deletion'), ('unknown', 'Unknown')], default='waiting', max_length=32)),
                ('cluster_id', models.IntegerField(blank=True, null=True)),
                ('spec_file', models.CharField(blank=True, max_length=255)),
                ('local', models.BooleanField(blank=True, default=False, help_text='Is this subtask to be run locally?')),
                ('custom_fields', models.CharField(blank=True, default='', max_length=10000)),
                ('job_count', models.IntegerField(default=-1, help_text='The count of the number of condor jobs. Only set after the subtask has finished. Use get_job_count() instead to find out job count')),
                ('run_time', models.FloatField(default=-1.0, help_text='The cumulative run time of associated condor jobs in days. Only set after the subtask has finished. Use get_run_time() to access.')),
                ('start_time', models.DateTimeField(blank=True, help_text='The time this subtask started running', null=True)),
                ('finish_time', models.DateTimeField(blank=True, help_text='The time the subtask stopped running', null=True)),
                ('task', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.task')),
            ],
            options={
                'ordering': ['index'],
            },
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
            name='ElasticIP',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_ip', models.GenericIPAddressField()),
                ('allocation_id', models.CharField(max_length=20, verbose_name='The allocation ID for the IP address')),
                ('association_id', models.CharField(max_length=20, verbose_name='The instance association ID for the address')),
                ('instance', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.ec2instance')),
                ('vpc', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web_interface.vpc')),
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
                ('status', models.CharField(choices=[('N', 'Not queued'), ('I', 'Idle'), ('R', 'Running'), ('H', 'Held'), ('F', 'Finished'), ('D', 'Mark for deletion'), ('U', 'Unknown'), ('E', 'Error')], max_length=1)),
                ('process_id', models.IntegerField(blank=True, null=True)),
                ('run_time', models.FloatField(null=True)),
                ('runs', models.PositiveIntegerField(blank=True, null=True, verbose_name='The number of runs this particular job is performing')),
                ('copasi_file', models.CharField(max_length=255)),
                ('subtask', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.subtask')),
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
                ('instance_type', models.CharField(choices=[('t1.micro', 't1.micro (<2 ECU, 1 Core, 613MB (Free tier eligible))'), ('m1.small', 'm1.small (1 ECU, 1 Core, 1.7GB)'), ('m1.medium', 'm1.medium (2 ECUs, 1 Core, 3.7GB)'), ('m1.large', 'm1.large (4 ECUs, 2 Cores, 7.5GB)'), ('m1.xlarge', 'm1.xlarge (8 ECUs, 4 Cores, 15GB)'), ('m2.xlarge', 'm2.xlarge (6.5 ECUs, 2 Cores, 17.1GB)'), ('m2.2xlarge', 'm2.2xlarge (13 ECUs, 4 Cores, 34.2GB)'), ('m2.4xlarge', 'm2.4xlarge (26 ECUs, 8 Cores, 68.4GB)')], max_length=20)),
                ('ec2_instance', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='web_interface.ec2instance')),
                ('ec2_pool', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web_interface.ec2pool')),
            ],
        ),
        migrations.AddField(
            model_name='ec2pool',
            name='vpc',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web_interface.vpc', verbose_name='Keypair'),
        ),
        migrations.AddField(
            model_name='ec2instance',
            name='ec2_pool',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web_interface.ec2pool'),
        ),
    ]