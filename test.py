import sqlite3, os, json
from tabulate import tabulate
import gradio as gr
from sqlalchemy import create_engine, MetaData
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain_community.llms import LlamaCpp  # Usa il wrapper corretto per llama-cpp
from langchain.prompts import PromptTemplate  # Importa la classe PromptTemplate

# Percorso del modello GGUF scaricato
MODEL_PATH = "./model/phi-2.Q6_K.gguf"  # Cambia con il tuo percorso

# Connessione al database SQLite
db_path = "dbweb.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Creiamo un oggetto SQLDatabase di LangChain, disabilitando il caricamento automatico di righe campione
db = SQLDatabase.from_uri(
    f"sqlite:///{db_path}",
    sample_rows_in_table_info=0  # ✅ Evita errori di parsing con colonne di tipo DATETIME
)
        
# Configura LLamaCpp per caricare Mistral 7B quantizzato
llm = LlamaCpp(
    model_path=MODEL_PATH,
    temperature=0.1,  # Bassa temperatura per risposte più deterministiche
    max_tokens=256,  # Numero massimo di token generati
    top_p=0.9,  # Controlla la diversità della generazione
    n_ctx=2048, # Contesto più grande per query più complesse
    n_batch=64,  # Imposta il valore di n_batch manualmente
    verbose=False #Disabilita i Log
)

# Creiamo la catena SQL automatica
db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)

query_utente="Mostrami l'elenco degli esercizi per le gambe (controlla la descrizione)"

risultati = db_chain.invoke({"query": query_utente})  # Esegue la query  

def clean_and_format_result(risultati):
    """ Pulisce e stampa il risultato della query in formato tabellare. """

    if 'result' not in risultati:
        print("\n❌ Risultato non trovato.")
        return

    result_data = risultati['result']  # Questo è il vero output della query

    print("\n📌 Risultati grezzi:", result_data)  # Debug

    if not result_data:
        print("\n⚠️ Nessun dato restituito dalla query.")
        return

    # ✅ Se il risultato è una lista di tuple, genera gli headers dinamicamente
    if isinstance(result_data, list) and all(isinstance(row, tuple) for row in result_data):
        headers = [f"Colonna {i+1}" for i in range(len(result_data[0]))]  # Genera header generici
        print("\n✅ Risultato della Query in formato tabellare:")
        print(tabulate(result_data, headers=headers, tablefmt="pretty"))

    # ✅ Se il risultato è una lista di dizionari
    elif isinstance(result_data, list) and all(isinstance(row, dict) for row in result_data):
        headers = result_data[0].keys()  # Usa le chiavi come intestazioni
        print("\n✅ Risultato della Query in formato tabellare:")
        print(tabulate(result_data, headers=headers, tablefmt="pretty"))

    else:
        # 🔴 Formato sconosciuto, stampa il risultato grezzo
        print("\n⚠️ Formato sconosciuto, stampa raw data:")
        print(result_data)


# 📌 Chiamata alla funzione
clean_and_format_result(risultati)