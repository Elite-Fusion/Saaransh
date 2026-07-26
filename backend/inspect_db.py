from sqlalchemy import create_engine, text
from backend.config.settings import get_settings

s = get_settings()
print(s.database_url)
engine = create_engine(s.database_url)
with engine.connect() as conn:
    print(conn.execute(text("select current_database()")).scalar())
    print(conn.execute(text("select to_regclass('public\"CaseMaster\"')")).scalar())
    print(conn.execute(text("select tablename from pg_tables where schemaname='public' order by tablename limit 20"))).fetchall())
