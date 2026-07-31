from __future__ import annotations


def test_store_schema_can_be_used(store_schema, llm_env_factory):
    from sql_agent import generate_sql

    env, _server = llm_env_factory(
        "SELECT c.City, SUM(o.TotalAmount) AS paid_sales "
        "FROM dbo.MockOrders o "
        "JOIN dbo.MockCustomers c ON c.CustomerId = o.CustomerId "
        "WHERE o.Status = 'paid' "
        "GROUP BY c.City;"
    )

    sql = generate_sql("فروش پرداخت‌شده هر شهر چقدر است؟", store_schema, env)

    assert "dbo.mockorders" in sql.lower()
    assert "paid" in sql.lower()


def test_university_schema_can_be_used(university_schema, llm_env_factory):
    from sql_agent import generate_sql

    env, _server = llm_env_factory(
        "SELECT c.CourseTitle, AVG(e.Grade) AS average_grade "
        "FROM dbo.MockEnrollments e "
        "JOIN dbo.MockCourses c ON c.CourseId = e.CourseId "
        "WHERE e.Semester = '1403-1' "
        "GROUP BY c.CourseTitle;"
    )

    sql = generate_sql("میانگین نمره هر درس در نیمسال 1403-1 چقدر است؟", university_schema, env)

    assert "dbo.mockenrollments" in sql.lower()
    assert "grade" in sql.lower()
