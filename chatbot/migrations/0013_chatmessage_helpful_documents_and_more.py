# Generated by Django 5.1.7 on 2025-05-02 09:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0012_chatmessage_user_disliked_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='helpful_documents',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='retrieve_queries',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
