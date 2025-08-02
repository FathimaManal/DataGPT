import os
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import google.generativeai as genai
import re
import streamlit as st

# --- Utility Functions ---

def clean_sql_query(sql_query):
    sql_query = re.sub(r"^(```|''')?\s*sql\s*", "", sql_query, flags=re.IGNORECASE)
    sql_query = re.sub(r"(```|''')$", "", sql_query)
    sql_query = sql_query.strip("`'\" \n")
    lines = [line.strip() for line in sql_query.splitlines() if line.strip()]
    for line in lines:
        if line.lower().startswith(('select', 'update', 'delete', 'insert', 'with')):
            return line
    return lines[0] if lines else sql_query

def generate_sql_query(model, question, table_name, table_info):
    prompt = f"""Given the following question and database schema, generate a valid SQLite SQL query.
Question: {question}

Database Schema:
Table: {table_name}
Columns: {table_info}

Return ONLY the SQL query, with NO explanation, NO comments, and NO formatting. Do NOT include ```sql or any markdown. Only output the SQL statement. The SQL query should be written so that the result is displayed in a well-formatted, readable table with clear column names and no extra text."""
    response = model.generate_content(prompt)
    return response.text.strip()

def try_model(model_name):
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say hello!")
        return model
    except Exception as e:
        return None

def generate_friendly_answer(model, question, result_df):
    # Convert the result DataFrame to a markdown table (or string)
    if result_df.empty:
        return "No results found."
    table_str = result_df.to_markdown(index=False)
    prompt = f"""Given the user's question and the following SQL result table, provide a concise, user-friendly, conversational answer (do not repeat the table, just summarize the result in plain English):
Question: {question}
SQL Result Table:
{table_str}
Answer:"""
    response = model.generate_content(prompt)
    return response.text.strip()

# --- Streamlit App ---
st.set_page_config(page_title="CSV SQL Chatbot", page_icon="🤖", layout="wide")

# --- Model and API Key Setup ---
@st.cache_resource
def load_model():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("GOOGLE_API_KEY not set. Please add it to your .env file.")
        st.stop()
    genai.configure(api_key=api_key)
    model = try_model('models/gemini-2.0-flash')
    if not model:
        model = try_model('models/text-bison-001')
    if not model:
        st.error("No supported Gemini model is available for your API key.")
        st.stop()
    return model

model = load_model()

# --- Database Setup ---
@st.cache_resource
def get_engine():
    return create_engine("sqlite:///chatbot.db")

engine = get_engine()

# --- Sidebar for Data Upload ---
st.sidebar.title("Upload Your Data")
uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])

# Default schema attributes
DEFAULT_COLUMNS = [
    "order_id", "customer_id", "customer_name", "product_id", "product_name", "category",
    "quantity", "price_per_unit", "total_amount", "order_date", "city", "country"
]
DEFAULT_DTYPES = [int, int, str, int, str, str, int, float, float, str, str, str]
DEFAULT_DATA = [
    [1, 101, "Alice", 201, "Widget", "Gadgets", 2, 19.99, 39.98, "2024-06-01", "New York", "USA"],
    [2, 102, "Bob", 202, "Gizmo", "Gadgets", 1, 29.99, 29.99, "2024-06-02", "Los Angeles", "USA"],
    [3, 103, "Charlie", 203, "Thingamajig", "Tools", 5, 9.99, 49.95, "2024-06-03", "London", "UK"],
    [4, 104, "David", 204, "Doodad", "Tools", 3, 14.99, 44.97, "2024-06-04", "Paris", "France"],
    [5, 105, "Eve", 205, "Doohickey", "Accessories", 4, 4.99, 19.96, "2024-06-05", "Berlin", "Germany"]
]

def create_default_table(engine):
    df = pd.DataFrame(DEFAULT_DATA, columns=DEFAULT_COLUMNS)
    df.to_sql('orders', engine, if_exists="replace", index=False)
    return df

# If no file is uploaded, create the default table
if 'db_ready' not in st.session_state:
    create_default_table(engine)
    st.session_state.table_name = 'orders'
    st.session_state.table_info = ", ".join(f"{col} (str)" for col in DEFAULT_COLUMNS)
    st.session_state.db_ready = True

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        table_name = os.path.splitext(uploaded_file.name)[0].replace(" ", "_")
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        st.session_state.table_name = table_name
        st.session_state.table_info = ", ".join(f"{col} ({dtype})" for col, dtype in df.dtypes.items())
        st.session_state.db_ready = True
        st.sidebar.success(f"Table '{table_name}' loaded successfully!")
        st.sidebar.info("You can now ask questions about your data.")
    except Exception as e:
        st.sidebar.error(f"Error loading file: {e}")
        st.session_state.db_ready = False

# --- Main Chat Interface ---
st.title("🤖 Chat with Your Orders Data")

if st.session_state.get("db_ready", False):
    st.info(f"Currently querying table: **{st.session_state.table_name}**")
    if "history" not in st.session_state:
        st.session_state.history = []
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Ask a question about your data:", "")
        submitted = st.form_submit_button("Send")
    if submitted and user_input:
        try:
            sql_query = generate_sql_query(model, user_input, st.session_state.table_name, st.session_state.table_info)
            cleaned_sql = clean_sql_query(sql_query)
            with engine.connect() as connection:
                result = connection.execute(text(cleaned_sql))
                rows = result.fetchall()
            result_df = pd.DataFrame(rows, columns=result.keys())
            friendly_answer = generate_friendly_answer(model, user_input, result_df)
            st.session_state.history.append({
                "question": user_input,
                "sql": cleaned_sql,
                "result_df": result_df,
                "friendly_answer": friendly_answer
            })
        except Exception as e:
            st.session_state.history.append({
                "question": user_input,
                "sql": cleaned_sql if 'cleaned_sql' in locals() else 'N/A',
                "error": str(e)
            })
    if st.session_state.history:
        for entry in reversed(st.session_state.history):
            st.markdown(f"**You:** {entry['question']}")
            st.markdown(f"**Generated SQL:**")
            st.code(entry['sql'], language="sql")
            if "result_df" in entry:
                st.markdown("**Result:**")
                st.dataframe(entry['result_df'])
            else:
                st.error(f"**Error:** {entry['error']}")
            if "friendly_answer" in entry:
                st.markdown(f"**Answer:** {entry['friendly_answer']}")
            st.markdown("---")
else:
    st.info("Please upload a CSV file in the sidebar to get started or use the default orders table.") 