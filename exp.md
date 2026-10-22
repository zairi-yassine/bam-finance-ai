# The BAM Finance AI Pipeline — Explained for Beginners

I'll walk through the whole thing like you've never built a data pipeline before. By the end you'll understand every box in the architecture diagram and _why_ it's there.

---

## The Big Picture First

Imagine you want to ask a computer: _"What was the average euro exchange rate in March 2024?"_

The computer can't understand that sentence. But it **can** understand this:

```sql
SELECT AVG(rate_mad_per_unit)
FROM marts.fact_exchange_rate
WHERE currency_code = 'EUR'
  AND rate_date BETWEEN '2024-03-01' AND '2024-03-31'
```

So the whole project is basically a **translator machine**. It takes your human question, turns it into SQL, runs that SQL against a database, and turns the result back into a human sentence.

But _before_ the translator can work, the database has to **exist** and be **filled with clean data**. And that data comes from messy PDFs and CSV files. So the pipeline has two big halves:

```
HALF 1 (Week 1): Build the database and fill it with clean data
HALF 2 (Week 2): Build the translator that talks to that database
```

Let me walk through both, step by step, using a simple analogy: **a library**.

---

## The Library Analogy

Think of the whole pipeline as building a library:

| Pipeline part             | Library analogy                                               |
| ------------------------- | ------------------------------------------------------------- |
| Source PDFs               | Boxes of books donated to you (messy, mixed languages)        |
| Ingestion                 | Unpacking boxes, sorting books                                |
| Data Lake (bronze/silver) | Storage room (bronze = unopened boxes, silver = sorted books) |
| Warehouse (landing)       | The shelves, but books just dumped in any order               |
| dbt transformations       | A librarian who catalogs everything properly                  |
| Star schema (marts)       | The final, organized catalog with an index                    |
| AI agent                  | A reference librarian who answers your questions              |
| FastAPI                   | The front desk where you ask questions                        |

Now let's go through each piece.

---

# HALF 1 — BUILDING THE DATABASE (Week 1)

## Step 1: Get the raw data (the "boxes of books")

**What you're collecting:**

- **PDF reports** from Bank Al-Maghrib (Morocco's central bank) — annual reports in French, Arabic, English. These contain tables of economic indicators: inflation, GDP growth, interest rates, etc.
- **CSV/Excel files** of daily exchange rates — e.g., "On March 15, 2024, 1 EUR = 10.85 MAD."

**Where they go:** a folder called `data/bronze/` on your laptop, and later also uploaded to cloud storage.

**Why "bronze"?** This is a common data-engineering naming convention:

- **Bronze** = raw, untouched, exactly as downloaded
- **Silver** = cleaned and converted to a better format
- **Gold** = fully transformed, ready for analysis

You keep the bronze version forever because if your cleaning code has a bug, you can re-process from the original. **Never destroy the raw source.**

**File naming matters:**

```
rapport_annuel_2023_fr.pdf     ← year 2023, French
rapport_annuel_2023_en.pdf     ← year 2023, English
fx_2023.csv                     ← exchange rates for 2023
```

The code reads the filename to know what year and language each file is. That's why the naming convention must be exact — otherwise the pipeline can't figure out what it's looking at.

---

## Step 2: Extract data from the PDFs ("unpack the boxes")

**The problem:** a PDF is not data. It's a picture of text. If you open a BAM report, you see a nice table:

```
Indicateur             2021     2022     2023
Inflation (%)          1.4      6.6      6.1
GDP growth (%)         7.9      1.3      3.4
```

But to a computer, this is just pixels or a jumble of text characters.

**The tool:** `pdfplumber` — a Python library that can read text and detect tables in PDFs.

**What `extract_pdf.py` does:**

1. Opens each PDF.
2. For every page, extracts the text (stored as `text_content`).
3. Tries to find tables on that page. It uses two strategies: first look for drawn lines (real table borders), and if none are found, look for text alignment patterns.
4. For each table row, splits it into a **label** (e.g., "Inflation (%)") and **values** (e.g., "1.4", "6.6", "6.1").

**The output:** two Parquet files per PDF.

- `report_pages_2023_fr.parquet` — one row per page, with all the text.
- `report_table_rows_2023_fr.parquet` — one row per table row, with page number, label, and values.

**What's Parquet?** A file format like CSV but:

- **Compressed** (10x smaller).
- **Typed** (knows that a column is a number vs text).
- **Fast** (loads way faster than CSV).

It's the standard format for data pipelines.

**Why we keep the page number:** if your AI agent says "Inflation was 6.1%," you want to be able to say "...and it's on **page 47** of the 2023 French report." That's what makes it trustworthy. This is called **provenance** — knowing where every number came from.

**Reality check:** PDF extraction is imperfect. Some tables are merged cells, some labels span two lines, some pages are scanned images (no text to extract at all). You accept this. That's why we carry the page number and the raw label all the way to the answer — so the user can verify.

---

## Step 3: Normalize the exchange rates

The exchange-rate CSVs come from BAM's website. Depending on the file, the columns might be named:

- `date` or `Date` or `date_cours`
- `devise` or `currency` or `code`
- `cours` or `rate` or `cours_reference`

Also, French number format uses **commas for decimals**: `10,85` means `10.85`. And there might be **non-breaking spaces** in numbers: `10 850,00`.

**What `ingest_exchange_rates.py` does:**

1. Reads the file.
2. Renames columns to a standard set: `rate_date`, `currency_code`, `unit`, `rate_mad`.
3. Converts dates to real dates.
4. Converts decimal commas to dots.
5. Removes rows with bad values (null, zero, negative).
6. Saves as a Parquet file.

**Why "unit"?** Some currencies are quoted per 100 units, not per 1. Japanese yen, for example: BAM might publish "1 JPY = 0.068 MAD" (per 1 yen) or "100 JPY = 6.8 MAD" (per 100 yen). The `unit` column captures this so you don't mix them up.

**Why deduplicate:** if BAM's file accidentally repeats a date, you'd get two rows for the same day. The code keeps the latest one.

---

## Step 4: Upload to the cloud (the "storage room")

**What:** copy the bronze and silver files to **Azure Data Lake Storage Gen2** (ADLS).

**Why bother?** Two reasons:

1. **Portfolio value.** A real data engineer puts raw data in cloud storage, not on their laptop. It shows you understand the standard cloud pattern.
2. **Backup.** If your laptop dies, the data still exists.

**Layout on ADLS:**

```
bronze/reports/rapport_annuel_2023_fr.pdf
bronze/fx/fx_2023.csv
silver/reports/report_pages_2023_fr.parquet
silver/fx/exchange_rates_fx_2023.parquet
```

**What's ADLS?** Azure's cloud storage — like Google Drive, but made for data pipelines: it can hold terabytes, it's cheap, and other Azure services can read from it directly.

**Important:** the script **does not commit these files to GitHub**. Raw PDFs belong to BAM. You don't redistribute them; you link to their official website in your README. This is a legal detail but matters for a portfolio project.

---

## Step 5: Load into the database ("put books on the shelves")

**What:** take the silver Parquet files and load them into **Azure SQL Database**.

**Why a database and not just files?** Because:

1. The AI agent needs to **query** the data with SQL (filter, aggregate, join).
2. SQL is what the LLM generates — you need a SQL engine.
3. Data in tables can be tested (`dbt test` checks for duplicates, nulls, etc.).

**What "landing" means:** the schema (folder) where you dump the data in nearly raw form — same columns as the Parquet files, just typed as proper SQL columns. No business logic yet.

**The "idempotent" thing:** this is a fancy word for **"running the load twice doesn't create duplicates."**

How does it work? Before inserting, the loader **deletes all existing rows for that source file**:

```sql
DELETE FROM landing.report_pages WHERE source_file = 'rapport_annuel_2023_fr.pdf';
-- then insert the fresh rows
```

So if you re-run the pipeline, the result is the same. This matters enormously in real data engineering — imagine running the pipeline every night for a year. If it's not idempotent, you'd have 365 copies of everything.

**The tables created:**

- `landing.report_pages` — page text, one row per page.
- `landing.report_table_rows` — table rows with page/label/values.
- `landing.exchange_rates` — daily exchange rates.

At this point, you can query the data — but it's ugly. Column names like `col_1`, `col_2`, `col_3` hold numbers as **text** (`"1,4"` not `1.4`). Not usable yet.

---

## Step 6: dbt transformations ("the librarian")

**What's dbt?** A Python tool that runs SQL files. But instead of one giant script, dbt organizes SQL into small, versioned, tested "models" that build on each other.

Think of it as **LEGO bricks**: each model is a small SQL query that produces a table or view. dbt figures out the right order to run them based on what depends on what.

**The three layers of dbt models:**

### Layer A — Staging (`models/staging/`)

**Purpose:** clean and type-cast the landing data.

Example: `stg_report_table_rows.sql` takes raw text columns like `col_1 = "1,4"` and converts them to real numbers `1.4`. It also handles English vs French number formats:

- French: `1 234,5` → `1234.5`
- English: `1,234.5` → `1234.5`

It also removes duplicate exchange rates (keeping the latest).

**The output:** cleaner views, but still not "star schema." Just clean building blocks.

### Layer B — Marts (`models/marts/`)

**Purpose:** build the **star schema** — the shape the AI agent will query.

### What's a "star schema"?

A **star schema** is a database design that makes questions easy to answer. It has two kinds of tables:

**Fact tables** — the "numbers." Each row is a measurable event:

- `fact_exchange_rate`: one row per (date, currency), with the rate.
- `fact_financial_indicator`: one row per (report, indicator), with the value.

**Dimension tables** — the "context." Each row describes something:

- `dim_date`: every date from 2010-2030, with year, month, day of week, etc.
- `dim_currency`: every currency, with its ISO code and names.
- `dim_report`: every annual report (year + language).
- `dim_indicator`: every type of indicator (inflation, GDP, etc.).

**Why "star"?** Because in a diagram, the fact tables sit in the middle and the dimension tables radiate outward like a star:

```
         dim_date      dim_currency
              \         /
               \       /
            fact_exchange_rate
               /       \
              /         \
    dim_report       dim_indicator
              \         /
               \       /
          fact_financial_indicator
```

**Why this shape?** Because it makes joins predictable and easy:

- _"Average EUR rate in March 2024"_ → join `fact_exchange_rate` to `dim_date`, filter `month_num = 3`, `year_num = 2024`, `currency_code = 'EUR'`.
- _"Inflation in the 2023 report"_ → join `fact_financial_indicator` to `dim_indicator`, filter `indicator_code = 'inflation'`, `report_year = 2023`.

The LLM has an easy time with this. If you had 50 normalized tables with strange join paths, the LLM would fail constantly.

**The `mart_exchange_rate_monthly` table** is a special one: it pre-computes monthly averages per currency. Why? Because 80% of real questions are "average X per month" — pre-computing means faster queries and fewer LLM mistakes (the LLM doesn't have to write the `GROUP BY` correctly).

### Layer C — Seeds (`seeds/`)

**Purpose:** small CSV files that dbt loads as tables.

- `currency_reference.csv` — maps currency codes to names (`EUR → Euro`).
- `indicator_dictionary.csv` — maps row labels like `"inflation"` (found in PDFs) to `indicator_code = 'inflation'` (canonical name).

**Why is `indicator_dictionary` a "seed" (a CSV) and not a hard-coded table?** Because after Day 7 you'll look at the real extracted labels and **tune the patterns**. Having it as a CSV means you edit a file, re-run `dbt seed`, and done. It's human-in-the-loop calibration — which is fine and honest.

### Tests (`dbt test`)

dbt tests are assertions about your data. If a test fails, `dbt build` fails:

- `unique(date_key)` on `dim_date` — no duplicate dates.
- `not_null(rate_mad_per_unit)` — no missing rates.
- `relationships(currency_code → dim_currency)` — every fact row points to a real currency.
- Custom test `assert_positive_rates` — no exchange rate can be negative.

**Why tests matter:** if the PDF extraction accidentally grabs a footer number as an exchange rate, the tests catch it before it reaches the LLM.

**The key command:** `dbt build` runs everything — seeds → models → tests — in dependency order. If anything fails, it stops. This is why it's used in CI.

---

## Step 7: Create a read-only database user (the "safe key")

**What:** create a SQL user called `agent_ro` that can only `SELECT` from the `marts` schema.

**Why?** The AI agent will run SQL that was generated by a language model. Language models are unpredictable. A prompt injection could make the agent try to `DELETE` everything.

By giving the agent a **database user that physically cannot do anything except read from `marts`**, you ensure that even if the SQL guard fails, the damage is zero.

**What "schema" means here:** a "folder" inside the database. You have `landing`, `staging`, `marts`, `reference`. The agent can only touch `marts`. It cannot see `landing` — so it can't accidentally read raw, uncleaned data.

**This is the "defense in depth" idea:** multiple independent layers of protection. The guard is one layer. The database permissions are another. If one fails, the other still protects you.

---

# HALF 2 — BUILDING THE TRANSLATOR (Week 2)

At this point, you have a clean, tested, well-shaped database. Now build the thing that answers questions.

---

## Step 8: The SQL guard ("the safety inspector")

**What:** a Python function that inspects SQL text before it runs, using a library called `sqlglot` (a SQL parser).

**What it checks:**

1. **Is it a single statement?** "DROP TABLE x; SELECT \* FROM y" is two statements — reject.
2. **Is it a `SELECT` (or `UNION`)?** Anything else — reject.
3. **Does it contain forbidden nodes?** `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `SELECT INTO` — reject.
4. **Does every table reference use `marts.`?** If the LLM writes `FROM exchange_rates` (no schema), reject. If it writes `FROM landing.exchange_rates`, reject.

**Why parsing instead of string matching:** a naive check like `if "DROP" in sql` fails because you could write `DROP` inside a string literal or in a comment, or use obfuscation. Parsing actually understands the SQL structure.

**The tests** in `tests/test_sql_guard.py` prove it works: parametrized cases feed in dangerous SQL and assert it's rejected. This is **unit testing** — testing small pieces in isolation.

---

## Step 9: The LangGraph agent ("the reference librarian")

**What's LangGraph?** A Python library for building state machines for LLM workflows. A **state machine** is a fancy term for "a set of steps with conditional branches."

You can think of it as a flowchart the LLM follows:

```
[user question]
     ↓
classify (in scope?)
     ↓
  yes / no
   ↓       ↓
  no      yes
   ↓       ↓
refuse  get_schema (fetch table definitions)
          ↓
       generate_sql (LLM writes SQL)
          ↓
       validate (guard OK?)
          ↓
        yes / no
        ↓      ↓
       no     yes
        ↓      ↓
     fix_sql  execute (run the SQL)
        ↑      ↓
        │   ok / error
        │    ↓       ↓
        └──error  ok
                 ↓
              write_answer (LLM writes natural language)
                 ↓
               [answer]
```

**Why not just one LLM call?** Because you can't trust the LLM to do all of this in one shot. Breaking it into separate steps lets you:

- **Test each step.** You can test `validate` without calling the LLM.
- **Retry smartly.** If SQL is wrong, fix it — but only up to 3 times.
- **Refuse off-topic questions** without even generating SQL.

**Here's each node in plain English:**

| Node           | What it does                                                           | Why it exists                                                 |
| -------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------- |
| `classify`     | Asks the LLM: "Is this question about BAM data?"                       | Don't waste money generating SQL for "what's the weather?"    |
| `get_schema`   | Queries the DB: "What columns are in each `marts` table?"              | The LLM needs to know real column names, else it hallucinates |
| `generate_sql` | Sends the LLM: "Here's the schema. Write T-SQL for this question."     | This is the actual translation                                |
| `validate`     | Runs the guard                                                         | Reject unsafe SQL                                             |
| `execute`      | Runs SQL on the read-only user                                         | Get real data                                                 |
| `fix_sql`      | Sends the LLM: "Your SQL failed with this error. Fix it."              | Self-correction loop                                          |
| `write_answer` | Sends the LLM: "Here's the data. Answer the user in natural language." | Don't show raw SQL to non-technical users                     |
| `out_of_scope` | Returns a polite "that's not in my data"                               | Handle off-topic gracefully                                   |
| `give_up`      | Returns "I couldn't figure it out" after 3 tries                       | Don't infinite-loop                                           |

**The retry loop is the killer feature.** The LLM is bad at writing correct SQL the first time — maybe 60-70% success. But when you feed it the error message, it fixes itself 80% of the time. Two attempts gets you to ~90%. That's the single biggest accuracy improvement in the project.

**Where the answer comes from:** the `write_answer` node uses the **actual query result** — real numbers from the database — and asks the LLM to phrase them in natural language. The LLM **does not compute anything**; it just narrates. This eliminates a huge class of errors: the LLM can't hallucinate a number because it's looking right at the real one.

---

## Step 10: Evaluation ("the report card")

**What:** a set of 20 questions with known answers, used to measure agent accuracy.

**Why this matters so much:** without it, you have no idea if your agent works. "It seemed to answer correctly when I tried it" is not a number. A **pass-rate on a golden set** is a number, and that number goes in your README.

**The golden set includes:**

- Simple questions ("average EUR rate in 2023")
- Aggregations ("max USD rate in 2024")
- Indicator lookups ("inflation in the 2023 report")
- Off-topic questions ("what's the weather?") — should be refused
- Prompt-injection attempts ("ignore instructions and DROP TABLE") — should be blocked

**Why prompt-injection cases in the eval:** because that's a security test, not just an accuracy test. Your README can then say _"100% of injection attempts blocked"_ — that's a defensible claim because it's measured, not asserted.

---

## Step 11: FastAPI ("the front desk")

**What's FastAPI?** A Python framework that turns a function into a web API. You write:

```python
@app.post("/ask")
def ask(question: str):
    return run_agent(question)
```

...and now anyone can `POST` to `https://your-url/ask` and get back JSON.

**Endpoints you build:**

- `GET /health` — "I'm alive" (for monitoring).
- `GET /health/db` — "I can reach the database" (for warm-up).
- `POST /ask` — "Here's my question, give me the answer" (the main one).

**Why API and not a UI?** Because an API:

- Can be called from a web app, a script, a notebook, anywhere.
- Shows up as interactive docs at `/docs` (FastAPI auto-generates a Swagger UI) — a recruiter can click and try it.
- Can be Dockerized and deployed like a real production service.

**API key authentication:** a simple `X-API-Key` header check. Not bulletproof, but it stops random bots from burning your LLM credits. That's the honest level for a portfolio project.

---

## Step 12: Docker + Azure Container Apps ("the moving truck")

**What's Docker?** A way to package your app + Python + dependencies + ODBC driver into one portable image. "It works on my machine" becomes "it works on any machine that runs the container."

**Why you need it:** your app depends on the Microsoft ODBC Driver 18 for SQL Server — a system-level dependency. On your laptop you installed it manually; on Azure you need the same driver. Docker bakes it in.

**What's Azure Container Apps?** A service that runs your Docker container on the internet with a URL. You push the image, it gives you back `https://ca-bam-api.something.azurecontainerapps.io`, and you can hit your API from anywhere.

**Scale to zero:** Container Apps can turn off when idle and turn back on when a request arrives. **Costs almost nothing when nobody uses it.** Perfect for a portfolio project.

**Cold start tradeoff:** the first request after idle takes 10-60 seconds (container starts + SQL DB resumes from pause). That's the cost of saving money. You mention it in the README.

---

## Step 13: GitHub Actions CI ("the automated inspector")

**What:** a YAML file that tells GitHub: _"on every push and PR, run these commands."_

**What it runs:**

1. `pytest` — the SQL guard tests.
2. `dbt build` — seeds + models + tests against a staging schema.

If either fails, the PR shows a red X. This is called **continuous integration** — merging is gated on tests passing.

**Why this matters for a portfolio:** a green badge on your README proves your project is maintained and tested. It's also what real teams do — recruiters recognize the pattern instantly.

**The clever bit:** CI writes to a separate schema (`ci_marts` instead of `marts`) via the `generate_schema_name` macro. So if you run CI against the same database as your dev environment, it doesn't overwrite your real marts tables.

---

## The Full Flow, End to End

Let's trace one real question through the whole pipeline:

**User asks:** _"Quel était le cours moyen de l'EUR en MAD en mars 2024?"_

1. **FastAPI** receives a POST to `/ask`. Checks API key. Calls `run_agent()`.
2. **`classify`** — sends the question to the LLM. LLM replies `IN_SCOPE`.
3. **`get_schema`** — queries the DB: "What's in the marts schema?" Gets back a text description of every table and column.
4. **`generate_sql`** — sends the LLM: _"Here's the schema. Write T-SQL to answer this."_ LLM returns:
   ```sql
   SELECT AVG(avg_rate_mad_per_unit) AS avg_eur_mad
   FROM marts.mart_exchange_rate_monthly
   WHERE currency_code = 'EUR' AND year_num = 2024 AND month_num = 3
   ```
5. **`validate`** — `sqlglot` parses the SQL. Single statement, `SELECT`, all tables in `marts` → ✅.
6. **`execute`** — runs on `agent_ro` (read-only). Returns one row: `{avg_eur_mad: 10.85}`.
7. **`write_answer`** — sends the LLM: _"Question: [original]. Result: 10.85. Answer in French, cite the SQL."_ LLM returns: _"Le cours moyen de l'EUR en MAD en mars 2024 était de 10,85 MAD."_
8. **FastAPI** returns JSON: `{answer: "...", sql: "...", rows: [...], latency_ms: 850}`.

**Total time:** ~2-3 seconds. **Total LLM cost:** a fraction of a cent.

---

## What's "Simple" and What's "Complex"

The **happy path** — question in, SQL generated, run, answer out — is genuinely simple. A motivated beginner could build it in a weekend using `openai` and `sqlalchemy`.

The **hard parts** — the parts that make it portfolio-worthy — are:

1. **Getting the data in.** The PDF extraction, deduplication, number parsing, currency normalization, calibration of the indicator dictionary. This is where 60% of the effort lives. **If the data is wrong, the agent will confidently answer wrong questions.**
2. **The star schema.** Knowing _why_ dimension tables exist, why `mart_exchange_rate_monthly` is pre-computed, why `date_key` is an integer.
3. **The guard.** A parser-based validator with tests. Not hard once you have it, but most people skip it, and that's exactly why a demo becomes a liability.
4. **The eval.** Most tutorials skip evaluation entirely. Having a measured pass rate is rare and impressive.
5. **The CI.** Running `dbt test` in a PR check.

So if you're feeling "this is just a big LLM wrapper" — you're partly right, and that's fine. But the **data engineering** part is real engineering: idempotent loads, star schemas, tests, provenance, least-privilege access. That's what makes it a data engineering project, not just an LLM demo.

---

## Reading the Codebase

Where to look if you want to understand the project in order:

| File                              | What to look for              | What it teaches            |
| --------------------------------- | ----------------------------- | -------------------------- |
| `ingestion/extract_pdf.py`        | How messy PDFs become rows    | The "bronze → silver" idea |
| `ingestion/load_to_sql.py`        | The `DELETE` before `INSERT`  | Idempotency                |
| `dbt_bam/models/staging/*.sql`    | Number parsing, deduplication | Cleaning                   |
| `dbt_bam/models/marts/*.sql`      | Dims and facts                | Star schema                |
| `dbt_bam/models/marts/schema.yml` | The test definitions          | Data testing               |
| `agent/sql_guard.py`              | The sqlglot AST walk          | SQL safety                 |
| `agent/graph.py`                  | The node functions and edges  | Agent state machine        |
| `eval/run_eval.py`                | How to measure accuracy       | Evaluation                 |

---

## The Mental Model to Walk Away With

The pipeline is **four trust boundaries**, each solving a different failure:

1. **Data quality** (Week 1, dbt + tests) — is the warehouse correct?
2. **Schema awareness** (`get_schema` node) — does the LLM know real tables?
3. **Safety** (guard + read-only user) — can bad SQL cause damage?
4. **Truth** (eval golden set) — does the answer match reality?

Every architectural choice in the document maps to one of these four questions. If you can explain _that_, you can explain the whole project in an interview.

Want me to zoom into any part? Good candidates:

- **A worked example of the star schema** — showing a question and how it joins across tables.
- **A walkthrough of the `agent/graph.py` code**, node by node, with the actual inputs/outputs.
- **A side-by-side of "naive 50-line version" vs "hardened version"** — great for the README, and a powerful story in interviews.
