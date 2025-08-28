# DataGPT - Natural Language to SQL Converter

DataGPT is an AI-powered tool that converts plain English queries into SQL, executes them on a database, and returns the results instantly. Perfect for people who want to interact with databases without writing SQL manually.

---

## 🚀 Features
- Convert natural language into SQL queries
- Execute queries directly on your database
- Supports filtering, sorting, and aggregations
- Simple web interface for asking questions
- Powered by OpenAI/GPT for query generation

---

## 🛠️ Tech Stack
- **Backend**: Flask (Python)
- **Frontend**: React (or HTML/CSS/JS if simple)
- **Database**: SQLite / MySQL / PostgreSQL (configurable)
- **AI Model**: OpenAI GPT API

---

## ⚡ How It Works
1. User enters a natural language query (e.g., *"Show me the top 5 customers by sales"*).
2. DataGPT converts it into SQL (e.g., `SELECT customer_name, SUM(sales) FROM orders GROUP BY customer_name ORDER BY SUM(sales) DESC LIMIT 5;`).
3. The SQL is executed on the database.
4. Results are displayed in a clean, readable table.

---
