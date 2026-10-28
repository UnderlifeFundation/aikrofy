#!/usr/bin/env python3
"""
Aikrofy Branding Migration Script
Updates database records that still reference the PymAI brand name.
Run once after deploying the Aikrofy rebranding.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extensions import db
from sqlalchemy import or_
from app import create_app
from models.agent import Agent
from models.company import Company

def main():
    app = create_app()
    with app.app_context():
        print("[Aikrofy Migration] Starting branding update...")
        
        # Update agents that have PymAI in their name or description
        agents = Agent.query.filter(
            or_(
                Agent.name.ilike('%pymai%'),
                Agent.name.ilike('%pymAI%'),
                Agent.name.ilike('%PymAI%'),
            )
        ).all()
        
        updated_agents = 0
        for agent in agents:
            old_name = agent.name
            agent.name = agent.name.replace('PymAI', 'Aikrofy').replace('pymai', 'Aikrofy').replace('Pymai', 'Aikrofy')
            if agent.description:
                agent.description = agent.description.replace('PymAI', 'Aikrofy').replace('pymai', 'Aikrofy')
            print(f"  Agent updated: '{old_name}' → '{agent.name}'")
            updated_agents += 1
        
        db.session.commit()
        print(f"[Aikrofy Migration] Updated {updated_agents} agents.")
        print("[Aikrofy Migration] Done!")

if __name__ == '__main__':
    main()
