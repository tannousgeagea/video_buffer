# Generated by Django 4.2 on 2024-10-03 09:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('database', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='image_format',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='video',
            name='video_format',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterModelTable(
            name='image',
            table='image',
        ),
        migrations.AlterModelTable(
            name='video',
            table='video',
        ),
    ]
