from database import get_connection, DATABASE_PATH, init_db

init_db()

print("DATABASE LOCATION:")
print(DATABASE_PATH)

with get_connection() as connection:
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    print("\nDATABASE TABLES:")

    for table in tables:
        print("\nTable:", table["name"])

        columns = connection.execute(
            f"PRAGMA table_info({table['name']})"
        ).fetchall()

        for column in columns:
            print(tuple(column))