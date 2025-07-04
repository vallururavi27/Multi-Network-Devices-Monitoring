# Generated by Django 5.2.3 on 2025-06-26 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0003_alter_device_device_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=7, help_text='Latitude coordinate', max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='device',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=7, help_text='Longitude coordinate', max_digits=10, null=True),
        ),
    ]
