"""Django management command to verify PostgreSQL connectivity and pgvector availability."""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Verifies PostgreSQL connectivity and checks whether the pgvector extension is available/installed."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== PostgreSQL & pgvector Verification ==="))
        
        # 1. Verify Database Engine
        db_engine = connection.settings_dict.get("ENGINE", "")
        db_name = connection.settings_dict.get("NAME", "")
        db_host = connection.settings_dict.get("HOST", "")
        db_port = connection.settings_dict.get("PORT", "")
        db_user = connection.settings_dict.get("USER", "")

        self.stdout.write(f"Database Engine: {db_engine}")
        self.stdout.write(f"Target Database: {db_name}")
        self.stdout.write(f"Host / Port    : {db_host}:{db_port}")
        self.stdout.write(f"Database User  : {db_user}")

        if "postgresql" not in db_engine:
            self.stderr.write(
                self.style.ERROR(
                    f"ERROR: Current database engine is '{db_engine}', not PostgreSQL. "
                    "Phase 0 requires PostgreSQL with pgvector integration."
                )
            )
            return

        # 2. Verify Connectivity
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                pg_version = cursor.fetchone()[0]
                self.stdout.write(self.style.SUCCESS(f"PostgreSQL Connectivity: SUCCESS\nServer Version: {pg_version}"))

                # 3. Check for vector extension in pg_available_extensions
                cursor.execute(
                    "SELECT name, default_version, installed_version, comment "
                    "FROM pg_available_extensions WHERE name = 'vector';"
                )
                ext_info = cursor.fetchone()

                if ext_info:
                    installed_ver = ext_info[2]
                    if installed_ver:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"pgvector Extension Status: INSTALLED & ACTIVE (Version: {installed_ver})"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"pgvector Extension Status: AVAILABLE in cluster (Version: {ext_info[1]}), but not yet activated in this DB.\n"
                                "Run 'python manage.py migrate' to activate it."
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            "pgvector Extension Status: UNAVAILABLE on host PostgreSQL server.\n"
                            "The 'vector' extension files (vector.dll, vector.control) are not installed in the PostgreSQL directories."
                        )
                    )
                    self.stdout.write("\n" + "-" * 70)
                    self.stdout.write("REQUIRED SETUP INSTRUCTIONS TO ENABLE PGVECTOR:")
                    self.stdout.write("-" * 70)
                    self.stdout.write("1. Open an Administrator Command Prompt or PowerShell.")
                    self.stdout.write("2. Open 'x64 Native Tools Command Prompt for VS 2026' (or VS 2022).")
                    self.stdout.write("3. Set the PostgreSQL root directory:")
                    self.stdout.write('   set "PGROOT=C:\\Program Files\\PostgreSQL\\18"')
                    self.stdout.write("4. Clone pgvector source code:")
                    self.stdout.write("   git clone https://github.com/pgvector/pgvector.git %TEMP%\\pgvector")
                    self.stdout.write("   cd %TEMP%\\pgvector")
                    self.stdout.write("5. Compile and install into PostgreSQL:")
                    self.stdout.write("   nmake /F Makefile.win")
                    self.stdout.write("   nmake /F Makefile.win install")
                    self.stdout.write("6. Verify in psql or re-run this command:")
                    self.stdout.write("   python manage.py verify_pgvector")
                    self.stdout.write("-" * 70 + "\n")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Connection Failed: {e}"))
