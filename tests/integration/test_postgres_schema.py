import os
import uuid

import psycopg2
import pytest
from psycopg2 import sql

from worldcup_pipeline.config import get_settings
from worldcup_pipeline.load import SCHEMA_PATH


@pytest.mark.integration
def test_schema_applies_in_isolated_postgres_schema():
    if os.getenv("RUN_DB_TESTS") != "1":
        pytest.skip("Set RUN_DB_TESTS=1 to run PostgreSQL integration tests.")

    schema_name = f"wc_pipeline_test_{uuid.uuid4().hex}"
    conn = psycopg2.connect(**get_settings().db_config)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
            cur.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema_name)))
            cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
            cur.execute("SELECT to_regclass(%s)", (f"{schema_name}.teams",))
            assert cur.fetchone()[0] == f"{schema_name}.teams"
    finally:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name)))
        conn.close()
