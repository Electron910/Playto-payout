import time
import sys
import os

import psycopg2


def wait_for_db():
    db_config = {
        'dbname': os.environ.get('DB_NAME', 'playto'),
        'user': os.environ.get('DB_USER', 'playto'),
        'password': os.environ.get('DB_PASSWORD', 'playto'),
        'host': os.environ.get('DB_HOST', 'db'),
        'port': os.environ.get('DB_PORT', '5432'),
    }

    max_retries = 30
    retry = 0

    while retry < max_retries:
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'merchants'"
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                print("DB tables are ready.")
                return True
            else:
                print(f"Tables not ready yet... ({retry + 1}/{max_retries})")
        except psycopg2.OperationalError:
            print(f"DB not reachable yet... ({retry + 1}/{max_retries})")
        except Exception as e:
            print(f"Error: {e} ({retry + 1}/{max_retries})")

        retry += 1
        time.sleep(3)

    print("Timed out waiting for database tables.")
    sys.exit(1)


if __name__ == '__main__':
    wait_for_db()