import streamlit as st
import sqlite3
import os
import re
import pandas as pd
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

# Load API key
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

# UI config
st.set_page_config(page_title="Ask Your HR Database", page_icon="📊")
st.title("📊 Ask Your HR Database")
st.caption("Ask questions in plain English (e.g., 'Show average salary by department')")

# Convert English to SQL
def generate_sql(question):
    prompt = f"""
You are an expert SQL assistant. Convert this natural language question into a valid SQLite SQL query.
Only return the SQL query — no formatting like ```.

Question: {question}
Table: employees (dynamic structure — use available columns in the table)
"""
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# Execute SQL query
def execute_sql_query(query):
    conn = sqlite3.connect("hr.db")
    try:
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        return rows, cols
    except Exception as e:
        return str(e), []
    finally:
        conn.close()

# Question input
question = st.text_input("Ask a question:")

if question:
    with st.spinner("⏳ Thinking..."):
        sql = generate_sql(question)
        st.subheader("💡 Generated SQL")
        st.code(sql, language="sql")
        result, cols = execute_sql_query(sql)

    if isinstance(result, str):
        st.error(f"❌ SQL Error: {result}")
    elif result:
        st.success("✅ Result:")
        st.dataframe([dict(zip(cols, row)) for row in result])
    else:
        st.warning("⚠️ No results found.")

# HR Insights
try:
    with sqlite3.connect("hr.db") as conn:
        cur = conn.cursor()

        cur.execute("SELECT AVG(salary) FROM employees WHERE department='HR'")
        avg_salary = cur.fetchone()[0]

        cur.execute("SELECT MAX(salary) FROM employees WHERE department='HR'")
        max_salary = cur.fetchone()[0]

        cur.execute("""
            SELECT name FROM employees 
            WHERE department='HR' 
            AND salary=(SELECT MAX(salary) FROM employees WHERE department='HR')
        """)
        top_earners = cur.fetchall()

    st.markdown("### 🔍 HR Department Salary Insights")
    st.markdown(f"**Average Salary in HR:** 💰 ${avg_salary or 'N/A'}")
    st.markdown(f"**Highest Salary in HR:** 🏆 ${max_salary or 'N/A'}")
    st.markdown("**Top Earning Employee(s):**")
    if top_earners:
        for name in top_earners:
            st.write(f"👤 {name[0]} (${max_salary})")
    else:
        st.write("No HR data available.")
except Exception:
    st.info("ℹ️ No HR data available to show insights yet.")

# Upload section
st.markdown("---")
st.header("📤 Upload a File (CSV or SQL)")
uploaded_file = st.file_uploader("Choose a CSV or SQL file", type=['csv', 'sql'])

if uploaded_file:
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    file_path = uploads_dir / uploaded_file.name

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success(f"✅ File uploaded: `{file_path.name}`")

    if file_path.suffix == ".csv":
        try:
            df = pd.read_csv(file_path)
            st.write("📄 Preview of uploaded CSV:")
            st.dataframe(df)

            with sqlite3.connect("hr.db") as conn:
                df.to_sql("employees", conn, if_exists="replace", index=False)
            st.success("📥 CSV data inserted into `employees` table.")
        except Exception as e:
            st.error(f"❌ Error inserting CSV data: {e}")

    elif file_path.suffix == ".sql":
        try:
            with open(file_path, "r") as sql_file:
                sql_script = sql_file.read()
            with sqlite3.connect("hr.db") as conn:
                cursor = conn.cursor()
                cursor.executescript(sql_script)
            st.success("📜 SQL script executed successfully.")
        except Exception as e:
            st.error(f"❌ SQL Execution Error: {e}")
