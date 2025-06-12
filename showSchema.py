def genera_schema_db(db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    schema = ""

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        schema += f"\nCREATE TABLE {table} (\n"

        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        col_defs = []
        pk_fields = []

        for col in columns:
            name = col[1]
            dtype = col[2]
            is_pk = col[5]
            col_defs.append(f"  {name} {dtype}")
            if is_pk:
                pk_fields.append(name)

        cursor.execute(f"PRAGMA foreign_key_list({table});")
        fks = cursor.fetchall()
        fk_defs = [
            f"  FOREIGN KEY ({fk[3]}) REFERENCES {fk[2]}({fk[4]})"
            for fk in fks
        ]

        all_defs = col_defs
        if pk_fields:
            all_defs.append(f"  PRIMARY KEY ({', '.join(pk_fields)})")
        all_defs += fk_defs

        schema += ",\n".join(all_defs) + "\n);\n"

    conn.close()
    return schema
