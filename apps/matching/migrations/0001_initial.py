"""Migration to enable the pgvector PostgreSQL extension.

Utilizes pgvector.django.VectorExtension to enable vector similarity search on
the PostgreSQL instance (Neon).
"""
from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        VectorExtension(),
    ]
