# Generated by Django 3.1.5 on 2021-07-15 02:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web_interface', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subtask',
            name='start_time',
            field=models.DateTimeField(blank=True, help_text='The time this subtask started running'),
        ),
    ]
