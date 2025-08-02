import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import google.generativeai as genai
import re

def setup_database():
    """Sets up an in-memory SQLite database and populates it with sample data."""
    engine = create_engine("sqlite:///:memory:")
    df = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'department': ['HR', 'Engineering', 'Engineering', 'Sales', 'HR'],
        'salary': [70000, 80000, 95000, 75000, 65000]
    })
    df.to_sql('employees', engine, index=False)
    return engine

def clean_sql_query(sql_query):
    # Remove code block markers and language hints
    sql_query = re.sub(r"^(```|''')?\s*sql\s*", "", sql_query, flags=re.IGNORECASE)
    sql_query = re.sub(r"(```|''')$", "", sql_query)
    # Remove any remaining backticks, triple quotes, or leading/trailing whitespace
    sql_query = sql_query.strip("`'\" \n")
    # If there are multiple lines, keep only the first non-empty line that looks like SQL
    lines = [line.strip() for line in sql_query.splitlines() if line.strip()]
    for line in lines:
        if line.lower().startswith(('select', 'update', 'delete', 'insert', 'with')):
            return line
    # Fallback: return the first line
    return lines[0] if lines else sql_query

def generate_sql_query(model, question, table_info):
    """Generate SQL query using Gemini model."""
    prompt = f"""Given the following question and database schema, generate a valid SQLite SQL query.
Question: {question}

Database Schema:
Table: employees
Columns: {table_info}

Return ONLY the SQL query, with NO explanation, NO comments, and NO formatting. Do NOT include ```sql or any markdown. Only output the SQL statement."""
    response = model.generate_content(prompt)
    return response.text.strip()

def try_model(model_name):
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say hello!")
        print(f"[Model: {model_name}] Test response: {response.text.strip()}")
        return model
    except Exception as e:
        print(f"[Model: {model_name}] Not available. Error: {e}")
        return None

def main():
    """Main function to run the chatbot."""
    # Load environment variables
    load_dotenv()

    # Check if the Google API key is set
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not set. Please add it to your .env file.")
        return

    try:
        # Configure Google Gemini
        genai.configure(api_key=api_key)
        
        # Try supported models in order
        model = try_model('models/gemini-2.0-flash')
        if not model:
            model = try_model('models/text-bison-001')
        if not model:
            print("No supported Gemini model is available for your API key. Please check your access or try a different key.")
            return

        # Setup database
        engine = setup_database()
        
        # Get table information
        table_info = "id (integer), name (text), department (text), salary (integer)"

        print("\nChatbot is ready! Ask questions about the employees database.")
        print("Available data: employee names, departments (HR, Engineering, Sales), and salaries")
        print("Type 'exit' to quit.\n")

        while True:
            question = input("> ")
            if question.lower() == 'exit':
                break

            try:
                # Generate SQL query
                sql_query = generate_sql_query(model, question, table_info)
                print(f"\nGenerated SQL Query: {sql_query}")

                cleaned_sql = clean_sql_query(sql_query)
                print(f"Cleaned SQL Query: {cleaned_sql}")

                # Execute the query and get the result
                with engine.connect() as connection:
                    result = connection.execute(text(cleaned_sql))
                    rows = result.fetchall()
                
                print("\nResult:")
                if not rows:
                    print("No results found.")
                else:
                    for row in rows:
                        print(row)
                print()

            except Exception as e:
                print(f"\nError: {str(e)}\n")

    except Exception as e:
        print(f"Failed to initialize the chatbot: {str(e)}")

if __name__ == "__main__":
    main() 