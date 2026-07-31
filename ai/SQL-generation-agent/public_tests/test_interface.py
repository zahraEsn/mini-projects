from __future__ import annotations

import inspect

def test_generate_sql_function_exists():
    from sql_agent import generate_sql

    assert inspect.isfunction(generate_sql)
    signature = inspect.signature(generate_sql)
    assert list(signature.parameters)[:3] == [
        "question",
        "schema",
        "env",
    ]


def test_generate_sql_returns_string(accounting_schema, llm_env_factory):
    from sql_agent import generate_sql

    env, _server = llm_env_factory(
        "SELECT FinancialYear, COUNT(DISTINCT DocNo) AS document_count "
        "FROM dbo.MockAccDocLines GROUP BY FinancialYear ORDER BY FinancialYear;"
    )

    sql = generate_sql("تعداد اسناد حسابداری به تفکیک سال؟", accounting_schema, env)

    assert isinstance(sql, str)
    assert sql.strip().lower().startswith("select")
