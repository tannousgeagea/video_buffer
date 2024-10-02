# Generated by Django 4.2 on 2024-10-02 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image_id', models.CharField(max_length=255, unique=True)),
                ('image_name', models.CharField(max_length=255)),
                ('image_file', models.ImageField(upload_to='images/')),
                ('image_size', models.IntegerField(blank=True, null=True)),
                ('image_format', models.CharField(blank=True, max_length=50, null=True)),
                ('timestamp', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_processed', models.BooleanField(default=False)),
                ('meta_info', models.JSONField(blank=True, null=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('source', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'verbose_name': 'Image',
                'verbose_name_plural': 'Images',
                'db_table': 'image',
            },
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('video_id', models.CharField(max_length=255, unique=True)),
                ('video_name', models.CharField(max_length=255)),
                ('video_file', models.FileField(upload_to='videos/')),
                ('video_size', models.IntegerField(blank=True, null=True)),
                ('video_format', models.CharField(blank=True, max_length=50, null=True)),
                ('timestamp', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('duration', models.DurationField(blank=True, null=True)),
                ('meta_info', models.JSONField(blank=True, null=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Video',
                'verbose_name_plural': 'Videos',
                'db_table': 'video',
            },
        ),
    ]
