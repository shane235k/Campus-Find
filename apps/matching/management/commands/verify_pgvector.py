"""Django management command to verify PostgreSQL connectivity, provider, and pgvector extension."""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Verifies PostgreSQL database provider, connectivity, and validates pgvector extension & operations."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== PostgreSQL & pgvector Verification ==="))

        db_engine = connection.settings_dict.get("ENGINE", "")
        db_name = connection.settings_dict.get("NAME", "")
        db_host = connection.settings_dict.get("HOST", "")
        db_port = connection.settings_dict.get("PORT", "")
        db_user = connection.settings_dict.get("USER", "")

        # Mask host if sensitive or cloud-based (keeping domain visible)
        masked_host = db_host
        if len(db_host) > 20 and "@" not in db_host:
            parts = db_host.split(".")
            if len(parts) > 2:
                masked_host = f"{parts[0][:6]}...{'.'.join(parts[-3:])}"

        self.stdout.write(f"Database Engine : {db_engine}")
        self.stdout.write(f"Target Database : {db_name}")
        self.stdout.write(f"Host Endpoint   : {masked_host}:{db_port or '5432'}")
        self.stdout.write(f"Database User   : {db_user}")

        # Provider detection
        is_neon = "neon.tech" in db_host or "neon" in db_name.lower()
        provider_name = "Neon Cloud PostgreSQL" if is_neon else "PostgreSQL"
        self.stdout.write(f"Detected Provider: {provider_name}")

        if "postgresql" not in db_engine:
            self.stderr.write(
                self.style.ERROR(
                    f"ERROR: Current database engine is '{db_engine}', not PostgreSQL."
                )
            )
            return

        try:
            with connection.cursor() as cursor:
                # 1. Connectivity & Server Version
                cursor.execute("SELECT version();")
                pg_version = cursor.fetchone()[0]
                self.stdout.write(self.style.SUCCESS(f"PostgreSQL Connectivity: SUCCESS\nServer Version: {pg_version}"))

                # 2. Ensure Extension
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                # 3. Verify via pg_extension
                cursor.execute(
                    "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
                )
                ext_record = cursor.fetchone()

                if ext_record:
                    ext_name, ext_version = ext_record
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"pgvector Extension Status: OPERATIONAL\n"
                            f"Extension Name : {ext_name}\n"
                            f"Active Version : {ext_version}"
                        )
                    )

                    # 4. Functional Test Query
                    cursor.execute("SELECT '[1,2,3]'::vector <-> '[4,5,6]'::vector AS test_distance;")
                    dist = cursor.fetchone()[0]
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Vector Math Test Query : SUCCESS (L2 Distance [1,2,3] <-> [4,5,6] = {dist:.4f})"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            "pgvector Extension Status: UNAVAILABLE\n"
                            "Extension 'vector' was not found in pg_extension after CREATE EXTENSION attempt."
                        )
                    )

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Connection/Verification Failed: {e}"))
