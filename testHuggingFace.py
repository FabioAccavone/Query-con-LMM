import os
import re
import ast
import warnings
import gradio as gr
import pandas as pd
import plotly.express as px
import json
from tabulate import tabulate
from langchain_community.utilities import SQLDatabase
from showSchema import genera_schema_db
import google.generativeai as genai

warnings.filterwarnings("ignore")

# Configura Gemini con la tua API key
GEMINI_API_KEY = "AIzaSyAt6h3SfV659TXo4qureoeUmuWZgnXl6Bg"
genai.configure(api_key=GEMINI_API_KEY)

def chiama_gemini(prompt: str) -> str:
    """
    Funzione helper per chiamare direttamente Google Gemini (modello gemini-2.0-flash)
    Restituisce la risposta testuale o un messaggio di errore.
    """
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            prompt.strip(),
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1500,
            },
        )
        return response.text.strip()
    except Exception as e:
        return f"⚠️ Errore con Gemini: {e}"

# Percorsi dei database SQLite
db_paths = {
    "garmin": "garmin.db",
    "garmin_monitoring": "garmin_monitoring.db",
    "garmin_summary": "garmin_summary.db",
}

def scegli_db_nlp(domanda):
    """
    Usa Gemini per scegliere quale database è più adatto per la domanda data.
    Ritorna la chiave del database ('garmin', 'monitoring', 'summary').
    """
    prompt = f"""
Sei un assistente esperto di dati sanitari Garmin e database SQLite.

Hai a disposizione **tre database** contenenti dati raccolti da dispositivi Garmin. Ogni database contiene tabelle diverse, adatte a specifici tipi di analisi. In base alla **seguente domanda** in italiano, scegli **esattamente uno** tra questi tre database, in base alla **presenza dei dati necessari** per rispondere correttamente.

Ecco i dettagli delle strutture dei tre database:

---

🟩 **`garmin_summary`**: contiene riepiloghi aggregati dei dati sanitari e di attività.
- Tabelle principali: `days_summary`, `weeks_summary`, `months_summary`, `years_summary`
- Metriche: sonno (totale e fasi), stress medio, battito cardiaco (rhr, hr), peso, passi, piani saliti, attività moderate/vigorose, calorie (totali, attive, BMR), idratazione, ossigenazione del sangue, respirazione.
- Frequenza: aggregazione per giorno, settimana, mese, anno.
- Ideale per: medie giornaliere o settimanali, correlazioni, confronti su periodo, trend temporali, confronti tra metriche aggregate.

---

🟦 **`garmin`**: contiene dati grezzi ed eventi.
- Tabelle principali: `sleep`, `stress`, `resting_hr`, `weight`
- Metriche: sonno (dettaglio con inizio/fine e punteggio), stress puntuale, frequenza cardiaca a riposo, passi giornalieri, calorie, idratazione, BB, SPO2, respirazione, piani saliti/discesi.
- Ideale per: accesso a dati **specifici**, interrogazioni sulle **misure puntuali o valori esatti** per un giorno.

---

🟨 **`garmin_monitoring`**: contiene dati a livello **di secondo o minuto** rilevati dal dispositivo.
- Tabelle principali: `monitoring`, `monitoring_hr`, `monitoring_intensity`, `monitoring_rr`, `monitoring_pulse_ox`
- Metriche: frequenza cardiaca continua, intensità attività, salite/discese, distanza, calorie attive, passi continui, ossigenazione del sangue, respiro.
- Ideale per: analisi ad alta risoluzione, pattern nel tempo (es. variazioni orarie), eventi specifici, correlazioni su base temporale fine.

---

📌 Quando ti viene posta una domanda, **scegli SOLO** il nome del database corretto tra:
- `garmin`
- `garmin_summary`
- `garmin_monitoring`

📌 Rispondi esclusivamente con il nome esatto del database. Nessuna spiegazione. Nessuna frase aggiuntiva.

---

DOMANDA:

{domanda}
"""

    risposta = chiama_gemini(prompt).lower()
    print(f"🔍 **Risposta da Gemini**: {risposta}")
    if risposta in db_paths:
        return risposta
    return "garmin"  # Default di fallback

def genera_query_sql(schema, domanda):
    """
    Genera una query SQL SQLite basata sullo schema del database e la domanda utente.
    Restituisce la query come stringa.
    """
    prompt = f"""
Dato il seguente schema del database:
{schema}

Domanda: {domanda}

Solo query SQLite completa e senza spiegazioni.
"""
    return chiama_gemini(prompt)

def pulisci_query_sql(text: str) -> str:
    """
    Estrae e pulisce una query SQL da un testo, rimuovendo:
    - blocchi markdown come ```sql
    - righe di testo non rilevanti (es. 'ite', intestazioni, ecc.)
    - tutto ciò che precede l'inizio effettivo della query (SELECT, WITH, ecc.)
    """
    # Rimuove blocchi ```sql o ```sqlite, se presenti
    text = re.sub(r"```(?:sql|sqlite)?\n?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")

    # Rimuove eventuali righe che non fanno parte di una query
    # e cerca una vera query SQL (inizia con SELECT, WITH, INSERT, ecc.)
    match = re.search(
        r"\b(SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\b[\s\S]+?(?=;|$)",
        text,
        flags=re.IGNORECASE,
    )

    return match.group(0).strip() + ";" if match else ""

def genera_risposta_naturale(domanda, query, risultati):
    """
    Genera una risposta in linguaggio naturale basata sulla domanda,
    la query eseguita e i risultati ottenuti.
    """
    prompt = f"""
Domanda dell'utente: {domanda}

Query eseguita:
{query}

Risultati ottenuti:
{risultati}

Genera una risposta in italiano, chiara e naturale, basata solo su questi dati.
"""
    return chiama_gemini(prompt)

def genera_config_grafico_gemini(domanda, query, risultati):
    prompt = f"""
Hai generato una query SQL e ottenuto dei dati.

Domanda: {domanda}
Query: {query}
Risultati:
{risultati}

Suggerisci il tipo di grafico nel seguente formato JSON:
{{
  "chart_type": "line",  // "bar", "scatter", "table"
  "x": "nome_colonna_x",
  "y": "nome_colonna_y"
}}
"""
    risposta = chiama_gemini(prompt)
   # ✅ Pulisce i blocchi markdown tipo ```json ... ```
    risposta_pulita = re.sub(r"```(?:json)?\n?", "", risposta, flags=re.IGNORECASE).strip()
    risposta_pulita = risposta_pulita.replace("```", "").strip()

    try:
        return json.loads(risposta_pulita)
    except json.JSONDecodeError:
        print(f"⚠️ Gemini ha restituito un JSON non valido:\n{risposta}")
        return {}

# Estrae le colonne da una query SQL
def estrai_colonne_da_select(query):
    # Rimuove newline e tabulazioni per facilitare regex
    query_single_line = " ".join(query.split())
    # Cerca tra SELECT e FROM il contenuto
    m = re.search(r"SELECT (.+?) FROM", query_single_line, flags=re.IGNORECASE)
    if m:
        cols_str = m.group(1)
        # Divide per virgola e pulisce ogni colonna
        columns = [c.strip().split(' ')[-1] for c in cols_str.split(",")]
        return columns
    return []

# Funzione per generare un grafico Plotly basato su un DataFrame
def genera_grafico_plotly(df, chart_type=None, x=None, y=None):
    if df.empty:
        raise ValueError("DataFrame vuoto.")

    # Pulizia colonne
    df.columns = [str(col).strip() for col in df.columns]
    print(f"📊 Colonne disponibili: {df.columns.tolist()}")
    print(df.head())

    # Identifica colonna temporale se presente
    date_col = next((col for col in df.columns if "date" in col.lower() or "day" in col.lower()), None)

    # Colonne numeriche
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    # Valori suggeriti da Gemini: validazione e fallback
    x_valido = x in df.columns
    y_valido = y in df.columns

    if not x_valido:
        print(f"⚠️ Colonna x '{x}' non valida. Uso fallback: {date_col}")
        x = date_col

    if not y_valido:
        fallback_y = numeric_cols[0] if numeric_cols else None
        print(f"⚠️ Colonna y '{y}' non valida. Uso fallback: {fallback_y}")
        y = fallback_y

    # Tipo di grafico predefinito se mancante
    if not chart_type:
        if x and y:
            chart_type = "line"
        elif len(numeric_cols) >= 2:
            chart_type = "scatter"
        elif numeric_cols:
            chart_type = "bar"
        else:
            chart_type = "table"

    print(f"📐 Grafico: {chart_type} | X: {x} | Y: {y}")

    try:
        if chart_type == "line" and x and y:
            return px.line(df, x=x, y=y, title=f"{y} nel tempo")
        elif chart_type == "bar" and x and y:
            return px.bar(df, x=x, y=y, title=f"Distribuzione di {y}")
        elif chart_type == "scatter" and x and y:
            return px.scatter(df, x=x, y=y, title=f"{x} vs {y}")
        else:
            return px.imshow(df.astype(str), text_auto=True, title="Tabella dati")
    except Exception as e:
        print(f"❌ Errore nella generazione del grafico: {e}")
        raise



# Funzione principale per eseguire la query e generare la risposta
def execute_query(domanda):
    try:
        db_key = scegli_db_nlp(domanda)
        db_path = db_paths[db_key]
        schema = genera_schema_db(db_path)

        query_raw = genera_query_sql(schema, domanda)
        query_sql = pulisci_query_sql(query_raw)

        print(f"\n📁 DB: `{db_key}`\n🧾 Query:\n{query_sql}")
        db = SQLDatabase.from_uri(f"sqlite:///{db_path}", sample_rows_in_table_info=0)
        result = db.run(query_sql)

        print(f"\n🔍 Risultato grezzo:\n{result}")

        # Costruzione DataFrame
        if isinstance(result, str):
            # Se result è una stringa JSON o simile, prova a caricarlo
            try:
                import ast
                result = ast.literal_eval(result)
            except:
                # Se non riesce, lo lascia così
                pass

        colonne = estrai_colonne_da_select(query_sql)
        print(f"📥 Colonne estratte dalla SELECT: {colonne}")

        if isinstance(result, list) and all(isinstance(row, (list, tuple)) for row in result):
            if len(result) > 0 and len(colonne) == len(result[0]):
                df = pd.DataFrame(result, columns=colonne)
            else:
                colonne_auto = [f"col{i}" for i in range(len(result[0]))]
                df = pd.DataFrame(result, columns=colonne_auto)
        else:
            df = pd.DataFrame([result])

        result_tab = tabulate(df, headers="keys", tablefmt="grid", showindex=False)

        # Qui stampo input e output della funzione di configurazione grafico
        print(f"\n🧠 Input per genera_config_grafico_gemini:\nDomanda: {domanda}\nQuery SQL: {query_sql}\nTabella risultante:\n{result_tab}\n")
        config = genera_config_grafico_gemini(domanda, query_sql, result_tab)
        print(f"🧠 Config grafico suggerita da Gemini:\n{config}")

        fig = genera_grafico_plotly(df, config.get("chart_type"), config.get("x"), config.get("y"))
        risposta_finale = genera_risposta_naturale(domanda, query_sql, result_tab)

        return risposta_finale, fig

    except Exception as e:
        print(f"❌ Errore: {e}")
        return f"❌ Errore: {e}", None



# Gradio UI
def gradio_interface(query):
    return execute_query(query)


with gr.Blocks() as demo:
    gr.Markdown("## 🔍 Interroga i tuoi dati Garmin con AI + Visualizzazione dinamica")

    with gr.Row():
        input_text = gr.Textbox(label="Scrivi la tua domanda:", lines=2)
        output_text = gr.Textbox(label="Risposta", interactive=False, lines=10)
    output_plot = gr.Plot(label="Grafico Generato")

    submit_button = gr.Button("Esegui Query")
    submit_button.click(fn=gradio_interface, inputs=input_text, outputs=[output_text, output_plot])

demo.launch()