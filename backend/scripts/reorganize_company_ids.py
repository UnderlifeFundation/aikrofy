"""
Reorganize Company IDs sequentially:
Target mapping:
  - 4 (Aikrofy AI Platform / Super Admin) -> 1
  - 1 (Weblifetech)                       -> 2
  - 7 (Empresa Prueba)                    -> 3
  - 11 (AI GovCoreX)                      -> 4
  - 12 (Fundación Underlife)              -> 5
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
import sqlalchemy as sa
from services.cache_service import CacheService

def reorganize():
    s = SessionLocal()
    inspector = sa.inspect(s.bind)
    
    # 1. Discover all tables that have company_id
    tables_with_company_id = []
    for t in inspector.get_table_names():
        if t == 'companies':
            continue
        cols = [c['name'] for c in inspector.get_columns(t)]
        if 'company_id' in cols:
            tables_with_company_id.append(t)
            
    print(f"Tables referencing company_id ({len(tables_with_company_id)}):")
    for t in tables_with_company_id:
        print(f"  - {t}")

    # The mapping: (old_id -> temporary_id -> target_id)
    # Using offset 1000 to prevent collisions during swap
    mapping = [
        (4,  1001, 1, "Aikrofy AI Platform"),
        (1,  1002, 2, "Weblifetech"),
        (7,  1003, 3, "Empresa Prueba"),
        (11, 1004, 4, "AI GovCoreX"),
        (12, 1005, 5, "Fundación Underlife"),
    ]

    try:
        # Disable FK checks
        s.execute(sa.text("SET FOREIGN_KEY_CHECKS = 0;"))
        
        # Step 1: Shift to temporary IDs (1001..1005)
        print("\n--- Step 1: Shifting to temporary IDs ---")
        for old_id, temp_id, _, name in mapping:
            print(f"Moving company '{name}' (ID {old_id} -> {temp_id})...")
            s.execute(sa.text(f"UPDATE companies SET id = {temp_id} WHERE id = {old_id};"))
            for t in tables_with_company_id:
                s.execute(sa.text(f"UPDATE `{t}` SET company_id = {temp_id} WHERE company_id = {old_id};"))

        # Step 2: Shift from temporary IDs to final target IDs (1..5)
        print("\n--- Step 2: Shifting from temp to target sequential IDs ---")
        for _, temp_id, target_id, name in mapping:
            print(f"Moving company '{name}' (temp {temp_id} -> target {target_id})...")
            s.execute(sa.text(f"UPDATE companies SET id = {target_id} WHERE id = {temp_id};"))
            for t in tables_with_company_id:
                s.execute(sa.text(f"UPDATE `{t}` SET company_id = {target_id} WHERE company_id = {temp_id};"))

        # Step 3: Explicitly verify and update users
        user_company_map = {
            'jonnathan.ypg@gmail.com': 1, # Aikrofy Super Admin
            'yosue.jpg@gmail.com': 2,     # Weblifetech
            'test@weblifetech.com': 3,    # Empresa Prueba
            'jonnathanyosue@gmail.com': 4,# AI GovCoreX
            'rubypg.05@gmail.com': 5,     # Fundación Underlife
        }
        for email, cid in user_company_map.items():
            s.execute(sa.text(f"UPDATE users SET company_id = {cid} WHERE email = '{email}';"))
            print(f"User {email} -> company_id = {cid}")

        # Step 4: Set auto increment to 6
        s.execute(sa.text("ALTER TABLE companies AUTO_INCREMENT = 6;"))
        print("\nSet companies AUTO_INCREMENT = 6")

        # Enable FK checks
        s.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1;"))
        
        s.commit()
        print("\nSUCCESS: All companies and references reorganized successfully!")
        
    except Exception as e:
        s.rollback()
        s.execute(sa.text("SET FOREIGN_KEY_CHECKS = 1;"))
        print(f"\nERROR during reorganization: {e}")
        raise e
    finally:
        s.close()

    # Clear redis session cache for all affected users
    for uid in range(1, 20):
        CacheService.delete(f"user:session:{uid}")
    print("Redis user session cache purged.")

if __name__ == '__main__':
    reorganize()
