"""Inspect Supabase schema — tables and columns."""
import psycopg2

conn = psycopg2.connect(
    host="aws-1-ap-south-1.pooler.supabase.com",
    port=6543,
    dbname="postgres",
    user="postgres.avnljqrvnthtxtnhjgkf",
    password="EliteFusion480@",
)
cur = conn.cursor()

# Tables
cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' ORDER BY table_name
""")
tables = [r[0] for r in cur.fetchall()]
print("=== TABLES ===")
for t in tables:
    print(t)

# Columns per table
print("\n=== COLUMNS ===")
for t in tables:
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        ORDER BY ordinal_position
    """, (t,))
    cols = cur.fetchall()
    print(f"\n-- {t}")
    for col, dtype, nullable in cols:
        print(f"  {col}  {dtype}  {'NULL' if nullable=='YES' else 'NOT NULL'}")

# Foreign keys
print("\n=== FOREIGN KEYS ===")
cur.execute("""
    SELECT
        tc.table_name, kcu.column_name,
        ccu.table_name AS foreign_table,
        ccu.column_name AS foreign_column
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
    ORDER BY tc.table_name, kcu.column_name
""")
for row in cur.fetchall():
    print(f"  {row[0]}.{row[1]} -> {row[2]}.{row[3]}")

conn.close()
