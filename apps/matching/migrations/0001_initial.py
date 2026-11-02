"""Migration to enable the pgvector PostgreSQL extension.

Utilizes pgvector.django.VectorExtension to ensure seamless integration with
PostgreSQL and the pgvector Python package.
"""
from django.db import migrations
from pgvector.django import VectorExtension


class SafeVectorExtension(VectorExtension):
    """PostgreSQL extension migration operation for pgvector.

    Subclasses pgvector.django.VectorExtension.
    Checks pg_available_extensions first. If available, creates the extension via
    standard VectorExtension logic. If unavailable on the host PostgreSQL server,
    reports the diagnostic notification with setup instructions and allows database
    operations to proceed cleanly.
    """

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_available_extensions WHERE name = 'vector';"
            )
            is_available = cursor.fetchone()

        if is_available:
            super().database_forwards(app_label, schema_editor, from_state, to_state)
        else:
            import sys
            sys.stderr.write(
                "\n" + "=" * 76 + "\n"
                "[PGVECTOR NOTICE] PostgreSQL extension 'vector' is not installed in the server.\n"
                "The migration checked: SELECT 1 FROM pg_available_extensions WHERE name = 'vector';\n"
                "Status: UNAVAILABLE on host PostgreSQL instance.\n"
                "Action Required: Install the pgvector binary into PostgreSQL before Phase 3.\n"
                "Refer to docs/ARCHITECTURE.md and docs/MATCHING_ENGINE.md for exact setup.\n"
                + "=" * 76 + "\n\n"
            )


class Migration(migrations.Migration):
    initial = True
    atomic = False

    dependencies = []

    operations = [
        SafeVectorExtension(),
    ]
