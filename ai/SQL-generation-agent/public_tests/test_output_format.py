from __future__ import annotations

def test_output_has_no_markdown_or_explanation(accounting_schema, llm_env_factory):
    from sql_agent import generate_sql

    env, _server = llm_env_factory(
        "```sql\n"
        "SELECT SUM(ABS(RialCost)) AS total_revenue "
        "FROM dbo.MockAccDocLines "
        "WHERE FinancialYear = '1403' AND Kol LIKE '6%';\n"
        "```"
    )

    sql = generate_sql("کل درآمد سال مالی ۱۴۰۳ چقدر است؟", accounting_schema, env)

    assert "```" not in sql
    assert not sql.lower().startswith("sql")
    assert sql.strip().lower().startswith("select")


def test_output_is_single_statement(accounting_schema, llm_env_factory):
    from sql_agent import generate_sql

    env, _server = llm_env_factory(
        "SELECT SUM(RialCost) FROM dbo.MockAccDocLines WHERE Kol LIKE '7%'; "
        "DELETE FROM dbo.MockAccDocLines;"
    )

    try:
        generate_sql("میزان هزینه‌های شرکت در سال 1403", accounting_schema, env)
    except ValueError:
        return

    raise AssertionError("multiple statements must be rejected")


def test_grouped_reports_may_return_multiple_columns(accounting_schema, llm_env_factory):
    from sql_agent import generate_sql

    env, _server = llm_env_factory(
        "SELECT FinancialYear, COUNT(DISTINCT DocNo) AS document_count "
        "FROM dbo.MockAccDocLines GROUP BY FinancialYear ORDER BY FinancialYear;"
    )

    sql = generate_sql("تعداد اسناد حسابداری به تفکیک سال؟", accounting_schema, env)

    assert "FinancialYear" in sql
    assert "COUNT" in sql.upper()
