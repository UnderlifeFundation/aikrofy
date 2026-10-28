"""
Company Skills API Routes - CRUD operations for dynamic agent skills.

Endpoints:
    GET    /api/companies/<id>/skills         - List all skills
    POST   /api/companies/<id>/skills         - Create a new skill
    PUT    /api/companies/<id>/skills/<sid>    - Update a skill
    DELETE /api/companies/<id>/skills/<sid>    - Delete a skill
    POST   /api/companies/<id>/skills/<sid>/rollback  - Rollback prompt version
    POST   /api/companies/<id>/skills/<sid>/toggle    - Enable/disable a skill
    POST   /api/companies/<id>/skills/seed    - Seed default system skills
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from database import get_db
from sqlalchemy.orm import Session

from models.company_skill import CompanySkill, SkillCategory, SkillOrigin
from services.skill_service import SkillService

router = APIRouter(prefix="/api/companies/{company_id}/skills", tags=["skills"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────

class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = "custom"
    system_prompt_block: str = Field(..., min_length=1)
    required_tools: Optional[List[str]] = []
    constraints: Optional[dict] = {}
    variables: Optional[dict] = {}
    priority: Optional[int] = 100
    is_enabled: Optional[bool] = True


class SkillUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    system_prompt_block: Optional[str] = None
    required_tools: Optional[List[str]] = None
    constraints: Optional[dict] = None
    variables: Optional[dict] = None
    priority: Optional[int] = None
    is_enabled: Optional[bool] = None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("")
def list_skills(company_id: int, db: Session = Depends(get_db)):
    """List all skills for a company."""
    skills = (
        CompanySkill.query
        .filter_by(company_id=company_id)
        .order_by(CompanySkill.priority.asc())
        .all()
    )
    return {"skills": [s.to_dict() for s in skills]}


@router.post("")
def create_skill(company_id: int, data: SkillCreate, db: Session = Depends(get_db)):
    """Create a new custom skill for a company."""
    # Check for duplicate name
    existing = CompanySkill.query.filter_by(
        company_id=company_id, name=data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Skill '{data.name}' already exists for this company."
        )

    # Validate category
    try:
        category = SkillCategory(data.category)
    except ValueError:
        category = SkillCategory.CUSTOM

    skill = CompanySkill(
        company_id=company_id,
        name=data.name,
        label=data.label,
        description=data.description,
        category=category,
        origin=SkillOrigin.MANUAL,
        system_prompt_block=data.system_prompt_block,
        required_tools=data.required_tools or [],
        constraints=data.constraints or {},
        variables=data.variables or {},
        priority=data.priority or 100,
        is_enabled=data.is_enabled if data.is_enabled is not None else True,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)

    # Sync to local Markdown file (Hybrid Architecture)
    try:
        SkillService.export_skill_to_markdown(skill)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to sync skill to disk on creation: {e}")

    return {"skill": skill.to_dict(), "message": "Skill created successfully."}


@router.put("/{skill_id}")
def update_skill(
    company_id: int, skill_id: int, data: SkillUpdate, db: Session = Depends(get_db)
):
    """Update an existing skill. Prompt changes are versioned automatically."""
    skill = CompanySkill.query.filter_by(
        id=skill_id, company_id=company_id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found.")

    # Update prompt with versioning
    if data.system_prompt_block is not None:
        skill.update_prompt(data.system_prompt_block)

    # Update other fields
    if data.label is not None:
        skill.label = data.label
    if data.description is not None:
        skill.description = data.description
    if data.category is not None:
        try:
            skill.category = SkillCategory(data.category)
        except ValueError:
            pass
    if data.required_tools is not None:
        skill.required_tools = data.required_tools
    if data.constraints is not None:
        skill.constraints = data.constraints
    if data.variables is not None:
        skill.variables = data.variables
    if data.priority is not None:
        skill.priority = data.priority
    if data.is_enabled is not None:
        skill.is_enabled = data.is_enabled

    db.commit()
    db.refresh(skill)

    # Sync to local Markdown file (Hybrid Architecture)
    try:
        SkillService.export_skill_to_markdown(skill)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to sync skill to disk on update: {e}")

    return {"skill": skill.to_dict(), "message": "Skill updated successfully."}


@router.delete("/{skill_id}")
def delete_skill(company_id: int, skill_id: int, db: Session = Depends(get_db)):
    """Delete a skill."""
    skill = CompanySkill.query.filter_by(
        id=skill_id, company_id=company_id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found.")

    # Delete local SKILL.md and directory (Hybrid Architecture)
    try:
        import os
        import shutil
        pymai_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        skill_dir = os.path.join(pymai_root, "uploads", "skills", f"company_{company_id}", skill.name)
        if os.path.exists(skill_dir):
            shutil.rmtree(skill_dir)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to delete local skill directory: {e}")

    db.delete(skill)
    db.commit()

    return {"message": f"Skill '{skill.name}' deleted successfully."}


@router.post("/{skill_id}/rollback")
def rollback_skill(company_id: int, skill_id: int, db: Session = Depends(get_db)):
    """Rollback a skill's prompt to its previous version."""
    skill = CompanySkill.query.filter_by(
        id=skill_id, company_id=company_id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found.")

    success = skill.rollback_prompt()
    if not success:
        raise HTTPException(
            status_code=400,
            detail="No previous version available for rollback."
        )

    db.commit()
    db.refresh(skill)

    # Sync to local Markdown file (Hybrid Architecture)
    try:
        SkillService.export_skill_to_markdown(skill)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to sync skill to disk on rollback: {e}")

    return {
        "skill": skill.to_dict(),
        "message": f"Skill '{skill.name}' rolled back to version {skill.version}."
    }


@router.post("/{skill_id}/toggle")
def toggle_skill(company_id: int, skill_id: int, db: Session = Depends(get_db)):
    """Toggle a skill's enabled/disabled state."""
    skill = CompanySkill.query.filter_by(
        id=skill_id, company_id=company_id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found.")

    skill.is_enabled = not skill.is_enabled
    db.commit()
    db.refresh(skill)

    # Sync to local Markdown file (Hybrid Architecture)
    try:
        SkillService.export_skill_to_markdown(skill)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to sync skill to disk on toggle: {e}")

    state = "enabled" if skill.is_enabled else "disabled"
    return {
        "skill": skill.to_dict(),
        "message": f"Skill '{skill.name}' {state}."
    }


@router.post("/seed")
def seed_skills(company_id: int, db: Session = Depends(get_db)):
    """Seed default system skills for a company (idempotent)."""
    created = SkillService.seed_default_skills(company_id, session=db)
    
    # Sync all company skills to disk (Hybrid Architecture)
    try:
        SkillService.export_all_company_skills(company_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to sync seeded skills to disk: {e}")

    return {
        "created": len(created),
        "skills": [s.to_dict() for s in created],
        "message": f"Seeded {len(created)} default skills."
    }


@router.post("/sync-to-files")
def sync_to_files(company_id: int, db: Session = Depends(get_db)):
    """Export all skills from database to markdown files on disk."""
    try:
        paths = SkillService.export_all_company_skills(company_id)
        return {
            "message": f"Successfully exported {len(paths)} skills to local markdown files.",
            "paths": paths
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error exporting skills to filesystem: {str(e)}"
        )


@router.post("/sync-from-files")
def sync_from_files(company_id: int, db: Session = Depends(get_db)):
    """Import and upsert all skills from local markdown files into the database."""
    try:
        skills = SkillService.import_skills_from_directory(company_id, session=db)
        return {
            "message": f"Successfully imported/updated {len(skills)} skills from local markdown files.",
            "skills": [s.name for s in skills]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error importing skills from filesystem: {str(e)}"
        )
