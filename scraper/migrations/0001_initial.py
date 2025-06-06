# Generated by Django 5.1.7 on 2025-03-15 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AllowedCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200, unique=True)),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="If unchecked, this category will be ignored by the crawler",
                    ),
                ),
                ("date_added", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Allowed Category",
                "verbose_name_plural": "Allowed Categories",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="NaverCafeData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("category", models.CharField(max_length=200)),
                ("content", models.TextField()),
                ("author", models.CharField(max_length=200)),
                ("published_date", models.DateTimeField(auto_now_add=True)),
                ("url", models.URLField(unique=True)),
                ("post_id", models.IntegerField()),
            ],
        ),
    ]
