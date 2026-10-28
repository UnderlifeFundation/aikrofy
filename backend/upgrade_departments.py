#!/usr/bin/env python3
"""
Enterprise Departments — Direct Database Upgrade Script
=========================================================
Applies the Enterprise Departments schema changes DIRECTLY to the MySQL database
without going through Alembic's version tracking.

This is the RECOMMENDED method for deploying to VPS when Alembic migrations
have complex dependency chains.

Changes applied:
  1. CREATE TABLE departments
  2. ALTER TABLE employees (add department_id, user_id, has_web_access)
  3. ALTER TABLE companies (add max_departments, max_employees)
  4. ALTER TABLE documents (add department_id)

Usage:
  cd /Users/macbook/Desktop/AI_LAB-WLT/aikrofy/backend
  python upgrade_departments.py

The script is IDEMPOTENT — it checks for column/table existence before applying
each change, so it is safe to run multiple times.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 60)
    print("  Aikrofy — Enterprise Departments DB Upgrade")
    print("=" * 60)

    # Import after sys.path setup
    from database import engine
    from sqlalchemy import text, inspect

    insp = inspect(engine)
    existing_tables = insp.get_table_names()

    with engine.connect() as conn:
        # ── 1. departments table ──────────────────────────────────────────
        if 'departments' not in existing_tables:
            print("\n[1/4] Creating table 'departments'...")
            conn.execute(text("""
                CREATE TABLE departments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    company_id INT NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    pinecone_namespace VARCHAR(255),
                    restrict_conversations TINYINT(1) NOT NULL DEFAULT 0,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX ix_departments_company_id (company_id),
                    CONSTRAINT departments_company_fk
                        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.commit()
            print("   ✅ Table 'departments' created.")
        else:
            print("\n[1/4] Table 'departments' already exists. Skipping.")

        # ── 2. employees columns ──────────────────────────────────────────
        print("\n[2/4] Checking 'employees' table columns...")
        emp_cols = {c['name'] for c in insp.get_columns('employees')}

        if 'department_id' not in emp_cols:
            print("   Adding column 'department_id'...")
            conn.execute(text("""
                ALTER TABLE employees
                ADD COLUMN department_id INT DEFAULT NULL,
                ADD INDEX ix_employees_department_id (department_id),
                ADD CONSTRAINT employees_department_fk
                    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL;
            """))
            conn.commit()
            print("   ✅ 'department_id' added.")
        else:
            print("   'department_id' already exists.")

        if 'user_id' not in emp_cols:
            print("   Adding column 'user_id'...")
            conn.execute(text("""
                ALTER TABLE employees
                ADD COLUMN user_id INT DEFAULT NULL UNIQUE,
                ADD CONSTRAINT employees_user_fk
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
            """))
            conn.commit()
            print("   ✅ 'user_id' added.")
        else:
            print("   'user_id' already exists.")

        if 'has_web_access' not in emp_cols:
            print("   Adding column 'has_web_access'...")
            conn.execute(text("""
                ALTER TABLE employees
                ADD COLUMN has_web_access TINYINT(1) NOT NULL DEFAULT 0;
            """))
            conn.commit()
            print("   ✅ 'has_web_access' added.")
        else:
            print("   'has_web_access' already exists.")

        # ── 3. companies quota columns ────────────────────────────────────
        print("\n[3/4] Checking 'companies' table columns...")
        comp_cols = {c['name'] for c in insp.get_columns('companies')}

        if 'max_departments' not in comp_cols:
            print("   Adding column 'max_departments'...")
            conn.execute(text("""
                ALTER TABLE companies
                ADD COLUMN max_departments INT NOT NULL DEFAULT 1;
            """))
            conn.commit()
            print("   ✅ 'max_departments' added.")
        else:
            print("   'max_departments' already exists.")

        if 'max_employees' not in comp_cols:
            print("   Adding column 'max_employees'...")
            conn.execute(text("""
                ALTER TABLE companies
                ADD COLUMN max_employees INT NOT NULL DEFAULT 10;
            """))
            conn.commit()
            print("   ✅ 'max_employees' added.")
        else:
            print("   'max_employees' already exists.")

        # ── 4. documents column ───────────────────────────────────────────
        print("\n[4/4] Checking 'documents' table columns...")
        doc_cols = {c['name'] for c in insp.get_columns('documents')}

        if 'department_id' not in doc_cols:
            print("   Adding column 'department_id'...")
            conn.execute(text("""
                ALTER TABLE documents
                ADD COLUMN department_id INT DEFAULT NULL,
                ADD INDEX ix_documents_department_id (department_id),
                ADD CONSTRAINT documents_department_fk
                    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL;
            """))
            conn.commit()
            print("   ✅ 'department_id' added.")
        else:
            print("   'department_id' already exists.")

    print("\n" + "=" * 60)
    print("  ✅  Enterprise Departments upgrade complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Restart the backend: pm2 restart aikrofy-backend")
    print("  2. Test the API: GET /api/departments/usage")
    print("  3. Create first department: POST /api/departments/")
    print()


if __name__ == '__main__':
    main()
