import os
import re
from typing import TypedDict
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from sqlalchemy import text
from common.db import make_engine
from agent.sql_guard import validate_sql


# --- 1. Define the State ---
class AgentState(TypedDict):
    question: str
    sql_query: str
    error: str
    answer: str
    rows: list[dict]
    attempts: int  # <--- ADDED TO STOP INFINITE LOOPS


# --- 2. Initialize the LLM ---
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0,
)
chain = llm | StrOutputParser()

# --- 3. Simplified Schema Context ---
SCHEMA_CONTEXT = """
You are an expert T-SQL Data Analyst for the Bank Al-Maghrib (BAM) AI Agent.
You have access to two tables in the `dbt_dev_marts` schema. 

TABLE 1: `dbt_dev_marts.fact_exchange_rate`
Use this table for currency exchange rates.
Columns:
- date_key (INT): Date in YYYYMMDD format.
- currency_code (VARCHAR): e.g., 'EUR', 'USD'.
- rate_mad (DECIMAL): The value in MAD.

TABLE 2: `dbt_dev_marts.fact_financial_indicator`
Use this table for macro-economic questions (inflation, GDP, etc.).
Columns:
- publication_year (INT): The report year (e.g., 2023).
- language (VARCHAR): 'en' or 'fr'.
- table_title (VARCHAR): e.g., 'Table 1.4.1'.
- indicator_name (VARCHAR): e.g., 'Consumer price index'.
- header_text (VARCHAR): The raw header text.
- column_index (INT): 1, 2, 3...
- indicator_value (DECIMAL): The actual number.


KNOWN INDICATOR NAMES (You MUST use these exact strings):
- 'Consumer price index' (This is the inflation rate)
- 'GDP'
- 'Current account'
- 'Official reserve assets'
- Clothing items and footwear
- Communications
- Education
- Entertainment and culture(1)
- Food products
- Furniture, household appliances and routine household maintenance
- Health(1)
- Housing, water, gas, electricity and other fuels(1)
- Miscellaneous goods and services(1)
- Restaurants and hotels
- Transport(2)
    -14,026 KDH betwee
    -3 percent increase
    -4.2 percenta
    -Advanced economies
    -Assets and investments in foreign currency
    -Assets and investments in gold
    -Automotive
    -Average lending rates
    -Bank loans
    -Banknotes and coins in circulation
    -Banks
    -Between 60 and 90 days
    -Between 90 and 120 days
    -Between end-2022
    -Bonds
    -Box 1.
    -Box 2.
    -Box 3.
    -Business properties
    -Capital goods
    -Cash and deposits
    -Cash and foreign currency deposits at the beginning of the year
    -Catégorie poids
    -Category
    -Certificates of deposit
    -Claims on Moroccan credit and assimilated institutions
    -Claims on Moroccan credit institutions and similar bodies
    -Claims on the Treasury
    -Commercial loans
    -Commercial papers
    -Commitments on securities
    -Commitments to international financial institutions
    -Consumer price index
    -Conversely, p
    -Core inflation indicator
    -Currency and deposits
    -Current account
    -Current expenditure
    -Current receipts
    -Customer payment deadlines
    -Depreciations of other costs to be spread out over many fiscal years
    -Depreciations of previous fiscal years
    -Depreciations of tangible and intangible fixed assets
    -Developed countries
    -Domestic demand (contribution in percentage pts)
    -Domestic Demand (contribution in pp)
    -Domestic demand (contribution in pts of percent)
    -Domestic tourists
    -Donations
    -Electronics and Electricity
    -Emerging and developing countries
    -Emerging and developing countries of Asia
    -Emerging and developing economies
    -Energy and lubricants
    -Equipment goods
    -Equity
    -Equity and related capital
    -Equity capital and the like
    -Exportations totales
    -Finance companies
    -Finance companies bills
    -Finance companies’ bills
    -Financial account (net flow)
    -Financial companies
    -Financial companies’ bills
    -Financial corporations
    -Financing capacity1
    -Financing requirement
    -Financing Requirement1
    -Fiscal balance3
    -Fixed assets
    -Foreign direct investments receipts
    -Foreign direct investments receipts (in % of GDP)
    -Foreign exchange operations - arbitrage operations
    -Foreign exchange operations - deposits in gold and in foreign currencies
    -Foreign exchange transactions- currency deposits
    -Foreign exchange transactions-arbitrage operations
    -Foreign exchange transactions-currency deposits
    -Foreign tourists
    -Fuels and lubricants
    -Funding Requirement1
    -Funding Requirement2
    -GDP
    -Gold stock (in tonnes)
    -Gold stock (in tons)
    -Greater than 120 days
    -Groups of products
    -Holdings and investments in foreign currencies
    -Holdings and investments in gold

RULES:
1. ALWAYS use fully qualified table names.
2. For currency questions, use `fact_exchange_rate`.
3. For report questions, use `fact_financial_indicator`.
4. **CRITICAL:** Do NOT try to calculate `column_index` from the `header_text`. The PDF extraction is messy and the columns are shifted. Just query the `indicator_name` and `publication_year`, and return ALL values. The user will see the trend.
5. Output ONLY valid T-SQL. Use `TOP 20`, NOT `LIMIT`.
6. NEVER output conversational text. Start directly with `SELECT`.
"""



def clean_sql(text: str) -> str:
    """Strips markdown and extracts only the SQL query."""
    text = text.replace("```sql", "").replace("```", "").strip()
    # Find everything from SELECT to the end
    match = re.search(r"(SELECT.*)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


# --- 4. Define the Nodes ---
def generate_sql(state: AgentState):
    print("🤖 Asking LLM to generate SQL...")
    response = chain.invoke([
        SystemMessage(content=SCHEMA_CONTEXT),
        HumanMessage(content=f"User Question: {state['question']}")
    ])
    sql = clean_sql(response)
    print(f"⚡ Executing SQL:\n{sql}\n")
    return {"sql_query": sql, "attempts": 0, "error": None}


def execute_sql(state: AgentState):
    print(f"⚡ Executing SQL:\n{state['sql_query']}\n")

    # 1. Validate the SQL first!
    is_valid, error_msg = validate_sql(state["sql_query"])
    if not is_valid:
        print(f"🛑 SQL Guard Blocked: {error_msg}")
        return {"error": f"Security Guard Blocked: {error_msg}"}

    # 2. If valid, execute it
    try:
        engine = make_engine(readonly=True)
        with engine.connect() as conn:
            result = conn.execute(text(state["sql_query"]))
            rows = [dict(zip(result.keys(), row)) for row in result.fetchall()]
        print(f"✅ SQL Executed successfully. Found {len(rows)} rows.")
        return {"rows": rows, "error": None}
    except Exception as e:
        print(f"❌ SQL Error: {str(e)[:200]}")
        return {"error": str(e)}


def check_for_errors(state: AgentState):
    if state.get("error"):
        if state.get("attempts", 0) >= 2:
            print("🛑 Max attempts reached. Giving up.")
            return "give_up"
        return "fix_sql"
    return "format_answer"


def fix_sql(state: AgentState):
    print(f"🔧 Attempt {state.get('attempts', 0) + 1} to fix SQL...")
    prompt = f"""
    The previous SQL failed with this error: {state['error']}
    The SQL was: {state['sql_query']}

    Fix the SQL. Output ONLY the corrected T-SQL query. No markdown, no explanations.
    """
    response = chain.invoke([HumanMessage(content=prompt)])
    sql = clean_sql(response)
    print(f"⚡ Retrying with fixed SQL:\n{sql}\n")
    return {"sql_query": sql, "attempts": state.get("attempts", 0) + 1, "error": None}


def format_answer(state: AgentState):
    prompt = f"Answer the question: '{state['question']}' using this data: {state['rows']}. Be concise."
    answer_text = chain.invoke([HumanMessage(content=prompt)])
    return {"answer": answer_text}


def give_up(state: AgentState):
    return {"answer": f"I tried to fix the SQL twice, but it kept failing. Last error: {state['error']}"}


# --- 5. Build the Graph ---
workflow = StateGraph(AgentState)
workflow.add_node("generate_sql", generate_sql)
workflow.add_node("execute_sql", execute_sql)
workflow.add_node("fix_sql", fix_sql)
workflow.add_node("format_answer", format_answer)
workflow.add_node("give_up", give_up)

workflow.set_entry_point("generate_sql")
workflow.add_edge("generate_sql", "execute_sql")
workflow.add_conditional_edges("execute_sql", check_for_errors, {
    "fix_sql": "fix_sql",
    "format_answer": "format_answer",
    "give_up": "give_up"
})
workflow.add_edge("fix_sql", "execute_sql")
workflow.add_edge("format_answer", END)
workflow.add_edge("give_up", END)

agent = workflow.compile()




# """" so the data is in the deltalake of azure right,
# the staging contains sql , this sql runs on which data , the parquet one?""""

