# Generated by Django 5.1.7 on 2025-04-21 12:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scraper', '0011_remove_navercafedata_notation_navercafedata_summary'),
    ]

    operations = [
        migrations.AddField(
            model_name='navercafedata',
            name='possible_questions',
            field=models.JSONField(blank=True, default=None, help_text='List of generated questions (strings) based on the content', null=True),
        ),
    ]
