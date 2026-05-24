from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='publication',
            name='indexing_status',
            field=models.CharField(
                choices=[
                    ('pending',    'En attente'),
                    ('extracting', 'Extraction'),
                    ('chunking',   'Découpage'),
                    ('uploading',  'Indexation'),
                    ('indexed',    'Indexé'),
                    ('failed',     'Échec'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
