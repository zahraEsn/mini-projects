from __future__ import annotations

import json
import re
import urllib.request
from typing import Iterable

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

# Statement keywords that are allowed to start a query.
ALLOWED_START_KEYWORDS = ("SELECT", "WITH")

# Keywords / statements that are never allowed anywhere in the query.
# Matched as whole SQL "words" (word boundaries), case-insensitively.
FORBIDDEN_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "MERGE",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "REVOKE",
    "DENY",
    "CALL",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "VACUUM",
    "BACKUP",
    "RESTORE",
    "DECLARE",
    "USE",
    "SHUTDOWN",
    "RECONFIGURE",
    "OPENROWSET",
    "OPENQUERY",
    "OPENDATASOURCE",
    "BULK",
    "INTO",
)

# SQL keywords / operators that should never be treated as a "column" or
# "table" candidate during schema validation.
SQL_KEYWORDS = {
    "SELECT",
    "FROM",
    "WHERE",
    "GROUP",
    "BY",
    "ORDER",
    "AS",
    "ON",
    "AND",
    "OR",
    "NOT",
    "IN",
    "LIKE",
    "BETWEEN",
    "IS",
    "NULL",
    "DESC",
    "ASC",
    "JOIN",
    "INNER",
    "LEFT",
    "RIGHT",
    "OUTER",
    "FULL",
    "CROSS",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "DISTINCT",
    "TOP",
    "WITH",
    "HAVING",
    "UNION",
    "ALL",
    "EXISTS",
    "INTERSECT",
    "EXCEPT",
    "OVER",
    "PARTITION",
    "LIMIT",
    "OFFSET",
    "FETCH",
    "ROWS",
    "ONLY",
    "FIRST",
    "NEXT",
    "TRUE",
    "FALSE",
    "UNKNOWN",
    "SOME",
    "ANY",
    "FOR",
    "CAST",
    "CONVERT",
}

# Common SQL functions the model may legitimately use. These are never
# validated as column/table names.
SQL_FUNCTIONS = {
    "COUNT",
    "SUM",
    "AVG",
    "MIN",
    "MAX",
    "ABS",
    "ROUND",
    "FLOOR",
    "CEILING",
    "YEAR",
    "MONTH",
    "DAY",
    "GETDATE",
    "SYSDATETIME",
    "ISNULL",
    "COALESCE",
    "NULLIF",
    "CONVERT",
    "CAST",
    "FORMAT",
    "DATEPART",
    "DATEDIFF",
    "DATEADD",
    "LEN",
    "LTRIM",
    "RTRIM",
    "TRIM",
    "UPPER",
    "LOWER",
    "SUBSTRING",
    "CONCAT",
    "REPLACE",
    "STDEV",
    "VAR",
    "ROW_NUMBER",
    "RANK",
    "DENSE_RANK",
    "LAG",
    "LEAD",
}

# Regular expressions used for parsing and validation
_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_QUALIFIED_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\b"
)
_STRING_LITERAL_RE = re.compile(r"'(?:[^']|'')*'")
_COMMENT_SINGLE_RE = re.compile(r"--[^\n]*")
_COMMENT_MULTI_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_FROM_JOIN_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+"
    r"(\[?[A-Za-z_][A-Za-z0-9_]*\]?(?:\s*\.\s*\[?[A-Za-z_][A-Za-z0-9_]*\]?)?)"
    r"(?:\s+(?:AS\s+)?(\[?[A-Za-z_][A-Za-z0-9_]*\]?))?",
    re.IGNORECASE,
)
_ALIAS_DEFINITION_RE = re.compile(
    r"\bAS\s+\[?([A-Za-z_][A-Za-z0-9_]*)\]?", re.IGNORECASE
)
_CTE_NAME_RE = re.compile(
    r"\bWITH\s+\[?([A-Za-z_][A-Za-z0-9_]*)\]?\s+AS\s*\(", re.IGNORECASE
)
_CTE_ADDITIONAL_RE = re.compile(
    r"\)\s*,\s*\[?([A-Za-z_][A-Za-z0-9_]*)\]?\s+AS\s*\(", re.IGNORECASE
)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def generate_sql(question: str, schema: dict, env: dict) -> str:
    """Translate `question` into a single, safe, read-only SQL statement.

    Raises:
      ValueError: if the question/schema are malformed, or if the model's
        output cannot be turned into a safe SQL statement that only
        references the given schema.
      RuntimeError: if the LLM endpoint cannot be reached at all.
    """

    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string.")
    if not isinstance(schema, dict) or "tables" not in schema:
        raise ValueError("schema must be a dict containing a 'tables' key.")
    if not env:
        raise ValueError("env is not valid.")

    tables = schema.get("tables") or {}
    if not tables:
        raise ValueError("schema['tables'] must not be empty.")

    prompt = _build_prompt(question, schema, env)
    raw_output = _call_llm(prompt, env)
    sql = _clean_sql(raw_output)
    _validate_sql(sql, tables)
    return sql


# --------------------------------------------------------------------------- #
# Prompt construction
# --------------------------------------------------------------------------- #


def _build_prompt(question: str, schema: dict, env: dict) -> list[dict]:
    dbms = env.get("SQL_DIALECT") or schema.get("dbms_type") or "SQLServer"
    database = schema.get("database", "")
    tables = schema.get("tables", {})
    business_rules = schema.get("business_rules", [])
    current_date = env.get("CURRENT_DATE", "")
    timezone = env.get("TIMEZONE", "")

    schema_lines = []
    for table, columns in tables.items():
        schema_lines.append(f"- {table}({', '.join(columns)})")
    schema_text = "\n".join(schema_lines)

    rules_text = "\n".join(f"- {rule}" for rule in business_rules) or "(none provided)"

    # Any column present in the schema whose name suggests it is a
    # category/dimension (route, city, channel, product, course, department,
    # status, type, ...) rather than a raw metric. These are the columns a
    # human analyst would normally break a rate/aggregate report down by,
    # even if the question doesn't literally name the column.
    dimension_hint_pattern = re.compile(
        r"(route|channel|category|city|region|branch|dept|department|"
        r"product|course|title|code|segment|team|agent|source|platform)",
        re.IGNORECASE,
    )
    # Columns already named inside a business rule are almost always used as
    # filter/enum values (e.g. "CallStatus = 'ANSWERED' means ..."), not as
    # report breakdown dimensions, so they are excluded from suggestions even
    # if their name also matches the hint pattern above.
    filter_columns = {
        col.lower() for col, _ in _QUALIFIED_RE.findall(" ".join(business_rules))
    } | {
        m.group(0).lower()
        for rule in business_rules
        for m in _IDENTIFIER_RE.finditer(rule.split("=")[0] if "=" in rule else "")
    }

    dimension_columns_by_table: dict[str, list[str]] = {}
    for table, columns in tables.items():
        dims = [
            c
            for c in columns
            if dimension_hint_pattern.search(c) and c.lower() not in filter_columns
        ]
        if dims:
            dimension_columns_by_table[table] = dims

    dims_text = (
        "\n".join(
            f"- {table}: {', '.join(cols)}"
            for table, cols in dimension_columns_by_table.items()
        )
        or "(none detected)"
    )

    style_reference = """
        STYLE REFERENCE (patterns to follow; do NOT reuse these table/column
        names unless they literally appear in the schema above):
        - "count of X per year" -> SELECT Year, COUNT(DISTINCT Id) AS x_count
          FROM T GROUP BY Year ORDER BY Year;
        - "answer/response rate" for a call-center-like table that has a
          route/channel column -> SELECT Route,
          SUM(CASE WHEN Status = 'ANSWERED' THEN 1 ELSE 0 END) AS answered_calls
          FROM T WHERE Type = 'incoming' GROUP BY Route;
          (breaking the rate down per route/channel is the expected report
          shape, not a single overall percentage.)
        - "sales per city" -> SELECT c.City, SUM(o.Amount) AS paid_sales
          FROM Orders o JOIN Customers c ON c.Id = o.CustomerId
          WHERE o.Status = 'paid' GROUP BY c.City;
        - "average grade per course" -> SELECT c.Title, AVG(e.Grade) AS average_grade
          FROM Enrollments e JOIN Courses c ON c.Id = e.CourseId
          WHERE e.Semester = '...' GROUP BY c.Title;
    """

    system_prompt = f"""You are a senior SQL developer. You write a single,
        read-only SQL query for the {dbms} dialect that answers the user's question.

        STRICT RULES (violating any of these makes the answer useless):
        1. Output ONLY raw SQL. No markdown fences, no explanation, no comments,
           no leading/trailing text of any kind.
        2. Output exactly ONE SQL statement. A single trailing semicolon is fine.
        3. The statement MUST start with SELECT or WITH. Never use INSERT, UPDATE,
           DELETE, DROP, ALTER, TRUNCATE, CREATE, MERGE, EXEC or any other
           data/schema modifying statement.
        4. Use ONLY the tables and columns listed below. Never invent a table or
           column that is not listed. Do not use SELECT *; list explicit columns.
        5. Qualify columns with table aliases when more than one table is used.
        6. For breakdown/aggregation questions, return the grouping column(s) plus
           the aggregated value(s), using GROUP BY and, when helpful, ORDER BY.
        7. DEFAULT TO BREAKING DOWN BY DIMENSION: if the question is about a
           rate, percentage, effectiveness, total, or comparison, and the
           relevant table has a category/dimension column (see "Detected
           dimension columns" below — e.g. route, channel, city, product,
           course, department, agent), you MUST include that column in
           SELECT and GROUP BY, even if the question doesn't name it
           explicitly. This is the standard, expected reporting shape.
           Only return a single ungrouped number when the question
           explicitly asks for one overall/total value (e.g. contains
           "overall", "in total", "across all", "grand total") or when no
           such dimension column exists in the relevant table.
        8. Prefer plain, directly-usable aggregates (COUNT, SUM, AVG per
           group) over inline percentage arithmetic unless the question
           explicitly asks for a computed ratio/percentage value itself.

        Database: {database}
        Tables and columns:
        {schema_text}

        Detected dimension columns (candidates for GROUP BY per rule 7):
        {dims_text}

        Business rules:
        {rules_text}

        Context:
        - current_date: {current_date}
        - timezone: {timezone}

        {style_reference}
    """

    user_prompt = f"Question: {question}\n\nReturn only the SQL statement."

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# --------------------------------------------------------------------------- #
# LLM call (OpenAI-compatible /v1/chat/completions)
# --------------------------------------------------------------------------- #


def _call_llm(messages: list[dict], env: dict) -> str:
    base_url = (env.get("LLM_BASE_URL") or "").rstrip("/")
    api_key = env.get("LLM_API_KEY", "")
    model = env.get("LLM_MODEL", "local-model")

    if not base_url:
        raise RuntimeError(
            "env['LLM_BASE_URL'] is required to call the language model."
        )

    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # network / HTTP errors
        raise RuntimeError(f"Failed to call LLM endpoint at {url}: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected LLM response shape: {data!r}") from exc


# --------------------------------------------------------------------------- #
# Output cleaning
# --------------------------------------------------------------------------- #


def _clean_sql(raw: str) -> str:
    """Strip markdown fences, comments, and surrounding prose, keeping only SQL."""

    if raw is None:
        raise ValueError("Model returned no output.")

    text = raw.strip()

    # Remove markdown fences
    fence_match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1)

    # Remove SQL comments
    text = _COMMENT_SINGLE_RE.sub("", text)
    text = _COMMENT_MULTI_RE.sub("", text)

    text = text.strip()

    # If there's still leading prose before the first SELECT/WITH keyword,
    # cut everything before it.
    keyword_match = re.search(r"\b(SELECT|WITH)\b", text, re.IGNORECASE)
    if keyword_match:
        text = text[keyword_match.start() :]
    else:
        raise ValueError("Model output does not contain a SELECT/WITH statement.")

    text = text.strip()

    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


def _validate_sql(sql: str, tables: dict[str, Iterable[str]]) -> None:
    if not sql:
        raise ValueError("Empty SQL after cleaning.")

    stripped = sql.strip()

    # 1. Must start with SELECT or WITH.
    first_word_match = re.match(r"\s*([A-Za-z]+)", stripped)
    first_word = first_word_match.group(1).upper() if first_word_match else ""
    if first_word not in ALLOWED_START_KEYWORDS:
        raise ValueError(
            f"Only SELECT/WITH statements are allowed; "
            f"got statement starting with '{first_word}'."
        )

    # Remove string literals to avoid false positives.
    scrubbed = _STRING_LITERAL_RE.sub(" ", stripped)

    # 2. Check for multiple statements.
    body = scrubbed.strip()
    if body.endswith(";"):
        body = body[:-1]

    # Check for remaining semicolons that might indicate multiple statements
    if ";" in body:
        # Check if there's a SQL keyword after the semicolon
        parts = body.split(";")
        for i, part in enumerate(parts):
            if i == 0:
                continue
            part_clean = part.strip()
            if part_clean and re.match(
                r"\b(SELECT|WITH|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b",
                part_clean,
                re.IGNORECASE,
            ):
                raise ValueError("Multiple SQL statements are not allowed.")

    # 3. Forbidden keywords / procedures anywhere in the statement.
    for word in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{word}\b", body, re.IGNORECASE):
            raise ValueError(f"Forbidden keyword detected: {word}")

    # 4. Extract referenced tables and validate against schema.
    schema_tables_by_bare_name: dict[str, str] = {}
    for full_name in tables.keys():
        bare = full_name.split(".")[-1]
        schema_tables_by_bare_name[bare.lower()] = full_name
        schema_tables_by_bare_name[full_name.lower()] = full_name

    # CTEs (`WITH cte_name AS (...)`) define pseudo-tables that are legal to
    # reference in FROM/JOIN even though they aren't part of the schema.
    cte_names = {m.group(1).lower() for m in _CTE_NAME_RE.finditer(body)}
    cte_names |= {m.group(1).lower() for m in _CTE_ADDITIONAL_RE.finditer(body)}

    alias_to_table: dict[str, str] = {}
    referenced_tables: set[str] = set()
    referenced_ctes: set[str] = set()

    for match in _FROM_JOIN_RE.finditer(body):
        raw_table = match.group(1).replace("[", "").replace("]", "").strip()
        raw_alias = match.group(2)
        raw_alias = (
            raw_alias.replace("[", "").replace("]", "").strip() if raw_alias else None
        )

        key = raw_table.lower()

        if key in cte_names:
            referenced_ctes.add(key)
            if raw_alias and raw_alias.upper() not in SQL_KEYWORDS:
                alias_to_table[raw_alias.lower()] = key
            alias_to_table[key] = key
            continue

        canonical = schema_tables_by_bare_name.get(key)
        if canonical is None:
            raise ValueError(f"Table '{raw_table}' is not part of the provided schema.")
        referenced_tables.add(canonical)

        if raw_alias and raw_alias.upper() not in SQL_KEYWORDS:
            alias_to_table[raw_alias.lower()] = canonical
        # A table can also be referenced by its own bare/full name (no alias).
        alias_to_table[raw_table.split(".")[-1].lower()] = canonical
        alias_to_table[raw_table.lower()] = canonical

    if not referenced_tables and not referenced_ctes:
        raise ValueError(
            "Could not find any valid FROM/JOIN table reference in the SQL."
        )

    # 5. Build the set of valid columns for the referenced tables, and
    #    collect any CTE / output aliases the query defines itself.
    valid_columns: set[str] = set()
    for full_name in referenced_tables:
        for col in tables[full_name]:
            valid_columns.add(col.lower())

    defined_aliases = {m.group(1).lower() for m in _ALIAS_DEFINITION_RE.finditer(body)}
    defined_aliases |= {m.group(1).lower() for m in _CTE_NAME_RE.finditer(body)}
    defined_aliases |= {m.group(1).lower() for m in _CTE_ADDITIONAL_RE.finditer(body)}

    # 6. Validate qualified references: alias.Column.
    for alias, column in _QUALIFIED_RE.findall(body):
        alias_l, column_l = alias.lower(), column.lower()
        if alias_l in alias_to_table:
            if column_l not in valid_columns and column_l not in defined_aliases:
                raise ValueError(
                    f"Column '{column}' is not part of table '{alias_to_table[alias_l]}'."
                )
        # If alias_l isn't a known table alias, it may be a CTE alias or a
        # schema/db prefix (e.g. dbo.Table) already handled above; we don't
        # fail here to avoid false positives on those legitimate cases.

    # 7. Validate bare (unqualified) identifiers that aren't keywords,
    #    functions, table names/aliases, numeric-looking tokens, or aliases
    #    defined by the query itself.
    qualified_spans = {m.span() for m in _QUALIFIED_RE.finditer(body)}

    def _inside_qualified(pos: int) -> bool:
        return any(start <= pos < end for start, end in qualified_spans)

    known_table_tokens = (
        {t.lower() for t in alias_to_table}
        | {t.split(".")[-1].lower() for t in referenced_tables}
        | {t.lower() for t in referenced_tables}
        | referenced_ctes
    )

    for match in _IDENTIFIER_RE.finditer(body):
        token = match.group(0)
        if _inside_qualified(match.start()):
            continue
        upper = token.upper()
        lower = token.lower()
        if upper in SQL_KEYWORDS or upper in SQL_FUNCTIONS:
            continue
        if upper in ALLOWED_START_KEYWORDS:
            continue
        if lower in known_table_tokens:
            continue
        if lower in valid_columns or lower in defined_aliases:
            continue
        if token.isdigit():
            continue
        # Bare identifiers that are not recognized as columns, tables,
        # aliases, keywords or functions are rejected as out-of-schema.
        raise ValueError(f"Identifier '{token}' is not part of the provided schema.")
