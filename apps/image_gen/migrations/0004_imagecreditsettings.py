from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("image_gen", "0003_image_size_and_style"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImageCreditSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("generation_credit_cost", models.PositiveIntegerField(default=5)),
                ("download_credit_cost", models.PositiveIntegerField(default=10)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Image Credit Settings",
                "verbose_name_plural": "Image Credit Settings",
            },
        ),
    ]
