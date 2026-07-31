from __future__ import annotations

def test_known_accounting_tables_are_allowed(accounting_schema, llm_env_factory):
    from sql_agent import generate_sql

    env, _server = llm_env_factory(
        "SELECT Month, MonthName, SUM(ABS(RialCost)) AS sales_amount "
        "FROM dbo.MockAccDocLines "
        "WHERE FinancialYear = '1403' AND Kol LIKE '6%' "
        "GROUP BY Month, MonthName ORDER BY CAST(Month AS int);"
    )

    sql = generate_sql(
        "میزان فروش در سال ۱۴۰۳ رو به تفکیک ماه نشون بده",
        accounting_schema,
        env,
    )
    assert "dbo.mockaccdoclines" in sql.lower()
    assert "financialyear" in sql.lower()


def test_unknown_tables_are_rejected(call_schema, llm_env_factory):
    from sql_agent import generate_sql

    env, _server = llm_env_factory("SELECT COUNT(*) FROM dbo.Payments;")

    try:
        generate_sql("چند پرداخت ثبت شده است؟", call_schema, env)
    except ValueError:
        return

    raise AssertionError("SQL referencing unknown tables must be rejected")
