def test_env_values_are_used_in_llm_request(accounting_schema, llm_env_factory):
    from sql_agent import generate_sql

    env, server = llm_env_factory("SELECT SUM(ABS(RialCost)) FROM dbo.MockAccDocLines;")

    assert generate_sql(
        "کل درآمد سال مالی ۱۴۰۳ چقدر است؟",
        accounting_schema,
        env,
    ).lower().startswith("select")
    assert len(server.requests) == 1
    assert server.requests[0]["model"] == env["LLM_MODEL"]


def test_env_context_is_sent_to_prompt(call_schema, llm_env_factory):
    from sql_agent import generate_sql

    env, server = llm_env_factory(
        "SELECT InboundRoute, COUNT(*) AS answered_calls "
        "FROM dbo.MockCallLogs WHERE CallType = 'incoming' GROUP BY InboundRoute;"
    )

    generate_sql("درصد پاسخ‌گویی در زمان استاندارد", call_schema, env)
    prompt_text = str(server.requests[0]["messages"])

    assert "SQLServer" in prompt_text
    assert "2026-06-15" in prompt_text
    assert "dbo.MockCallLogs" in prompt_text
