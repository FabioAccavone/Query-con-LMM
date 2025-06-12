import sqlite3
import mysql.connector
import datetime

# Connessione al database MySQL
mysql_db = mysql.connector.connect(
    host="localhost",      # Indirizzo del server MySQL (localhost se è sullo stesso computer)
    user="root",           # Il tuo username MySQL
    password="ProgrammazioneWeb2025",   # La tua password MySQL
    database="dbweb"  # Nome del tuo database
)

# Connessione al database SQLite
sqlite_conn = sqlite3.connect('dbweb.db')
sqlite_cursor = sqlite_conn.cursor()

# Funzione per convertire oggetti datetime.timedelta in secondi
def convert_timedelta(value):
    if isinstance(value, datetime.timedelta):
        return value.total_seconds()  # Converti in secondi
    return value  # Se non è timedelta, lascia il valore invariato

# Funzione per convertire datetime in stringa ISO 8601
def convert_datetime(value):
    if isinstance(value, datetime.datetime):
        return value.isoformat()  # Converti in formato stringa ISO 8601
    return value  # Se non è datetime, lascia il valore invariato

# Funzione per copiare i dati da MySQL a SQLite
def copy_data():
    # Ottieni tutte le tabelle dal database MySQL
    mysql_cursor = mysql_db.cursor()
    mysql_cursor.execute("SHOW TABLES")
    tables = mysql_cursor.fetchall()

    for table in tables:
        table_name = table[0]
        print(f"Transfering table: {table_name}")

        # Ottieni la struttura della tabella MySQL
        mysql_cursor.execute(f"DESCRIBE {table_name}")
        columns = mysql_cursor.fetchall()
        
        # Crea la tabella in SQLite
        create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ("
        for column in columns:
            create_table_query += f"{column[0]} {column[1]}, "
        create_table_query = create_table_query.rstrip(", ") + ")"
        sqlite_cursor.execute(create_table_query)

        # Copia i dati dalla tabella MySQL a SQLite
        mysql_cursor.execute(f"SELECT * FROM {table_name}")
        rows = mysql_cursor.fetchall()

        # Converti ogni valore di tipo timedelta e datetime
        rows = [
            tuple(convert_timedelta(convert_datetime(value)) for value in row)  # Converte datetime e timedelta
            for row in rows
        ]
        
        # Inserisci i dati nel database SQLite
        insert_query = f"INSERT INTO {table_name} VALUES ({', '.join(['?' for _ in range(len(columns))])})"
        sqlite_cursor.executemany(insert_query, rows)

    # Salva le modifiche e chiudi
    sqlite_conn.commit()

# Esegui la conversione
copy_data()

# Chiudi le connessioni
mysql_db.close()
sqlite_conn.close()

print("Conversione completata con successo!")
