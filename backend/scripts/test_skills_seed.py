import os
import sys

# Ensure backend folder is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db_session
from models.company import Company
from services.skill_service import SkillService

def main():
    try:
        companies = db_session.query(Company).all()
        print(f"Found {len(companies)} companies in database.")
        for comp in companies:
            print(f"Company ID: {comp.id}, Name: {comp.name}")
            seeded = SkillService.seed_default_skills(comp.id, session=db_session)
            print(f"Seeded {len(seeded)} default skills for company {comp.id}.")
            
            # Let's list files to verify sync on disk
            pymai_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            skills_dir = os.path.join(pymai_root, "uploads", "skills", f"company_{comp.id}")
            if os.path.exists(skills_dir):
                print(f"Local files generated at {skills_dir}: {os.listdir(skills_dir)}")
            else:
                print(f"Directory NOT generated at {skills_dir}")
                
    except Exception as e:
        print(f"Error during seeding test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.remove()

if __name__ == "__main__":
    main()
