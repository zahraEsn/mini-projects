from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "dangerous_sql",
    [
        "DROP TABLE dbo.MockAccDocLines;",
        "DELETE FROM dbo.MockAccDocLines;",
        "UPDATE dbo.MockAccDocLines SET RialCost = 0;",
        "INSERT INTO dbo.MockAccDocLines(DocNo) VALUES (1);",
        "ALTER TABLE dbo.MockCallLogs ADD NewColumn INTEGER;",
        "TRUNCATE TABLE dbo.MockCallLogs;",
    ],
)
def test_dangerous_sql_is_rejected(accounting_schema, llm_env_factory, dangerous_sql):
    from sql_agent import generate_sql

    env, _server = llm_env_factory(dangerous_sql)

    with pytest.raises(ValueError):
        generate_sql("همه اسناد حسابداری را حذف کن", accounting_schema, env)


def test_read_only_cte_is_allowed(accounting_schema, llm_env_factory):
    from sql_agent import generate_sql

    env, _server = llm_env_factory(
        "WITH docs AS ("
        "SELECT DocNo FROM dbo.MockAccDocLines WHERE FinancialYear = '1403'"
        ") SELECT COUNT(DISTINCT DocNo) FROM docs;"
    )

    sql = generate_sql("تعداد اسناد حسابداری سال ۱۴۰۳", accounting_schema, env)

    assert sql.strip().lower().startswith("with")
