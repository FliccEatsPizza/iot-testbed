"""
One-shot migration: update all devices with device_type='border_router'
to device_type='physical' in the server's SQLite/SQLAlchemy database.

Run ONCE on the server (laptop) after pulling the ipfree branch:
  .venv\Scripts\python.exe migrate_remove_border_router.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, engine
import sqlalchemy as sa

def migrate():
    with engine.connect() as conn:
        result = conn.execute(
            sa.text("SELECT id, name, device_type FROM devices WHERE device_type = 'border_router'")
        )
        rows = result.fetchall()
        if not rows:
            print("✅ No border_router devices found — nothing to migrate.")
            return

        print(f"Found {len(rows)} border_router device(s):")
        for row in rows:
            print(f"  ID={row[0]}, name={row[1]}, type={row[2]}")

        conn.execute(
            sa.text("UPDATE devices SET device_type = 'physical' WHERE device_type = 'border_router'")
        )
        conn.commit()
        print(f"✅ Migrated {len(rows)} device(s) from 'border_router' → 'physical'.")
        print("   These dongles can still run border-router firmware — detection now happens")
        print("   automatically via Makefile content when you upload rpl_border_router.zip.")

if __name__ == "__main__":
    migrate()
