"""
Sync Skills Script - Updates default skills in MySQL and purges Redis cache.
"""
import os
import json
import logging
from app import create_app
from extensions import db
from models.company import Company
from models.company_skill import CompanySkill
from services.skill_service import SkillService, DEFAULT_SYSTEM_SKILLS
from services.cache_service import CacheService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sync_skills_db")

def sync_skills():
    app = create_app()
    with app.app_context():
        companies = Company.query.all()
        logger.info(f"Syncing system skills for {len(companies)} companies...")

        for company in companies:
            for target_skill_def in DEFAULT_SYSTEM_SKILLS:
                skill = CompanySkill.query.filter_by(company_id=company.id, name=target_skill_def['name']).first()
                if skill:
                    logger.info(f"Updating {target_skill_def['name']} for company ID {company.id} ({company.name})...")
                    skill.label = target_skill_def['label']
                    skill.description = target_skill_def['description']
                    skill.system_prompt_block = target_skill_def['system_prompt_block']
                    skill.required_tools = target_skill_def.get('required_tools', [])
                    skill.priority = target_skill_def['priority']
                else:
                    logger.info(f"Seeding missing {target_skill_def['name']} for company ID {company.id} ({company.name})...")
                    skill = CompanySkill(
                        company_id=company.id,
                        name=target_skill_def['name'],
                        label=target_skill_def['label'],
                        description=target_skill_def['description'],
                        category=target_skill_def['category'],
                        priority=target_skill_def['priority'],
                        is_enabled=target_skill_def.get('is_enabled', True),
                        required_tools=target_skill_def.get('required_tools', []),
                        system_prompt_block=target_skill_def['system_prompt_block']
                    )
                    db.session.add(skill)

            # Purge Redis cache for this company
            cache_key = f"skills:company_{company.id}"
            try:
                CacheService.delete(cache_key)
                logger.info(f"Purged Redis cache for key {cache_key}")
            except Exception as e:
                logger.warning(f"Cache purge warning for {cache_key}: {e}")

        db.session.commit()
        logger.info("Successfully updated all company skills and purged cache.")

if __name__ == '__main__':
    sync_skills()
