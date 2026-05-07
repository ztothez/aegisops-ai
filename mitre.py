import os
import streamlit as st
from mitreattack.stix20 import MitreAttackData

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@st.cache_resource
def load_mitre():
    return MitreAttackData(os.path.join(BASE_DIR, "enterprise-attack.json"))

def get_technique_details(technique_id: str) -> str:
    try:
        mitre = load_mitre()  # cached
        techniques = mitre.get_techniques(include_subtechniques=True)
        
        technique = next(
            (t for t in techniques if t.get("external_references") and
             any(ref.get("external_id") == technique_id 
                 for ref in t.get("external_references", []))),
            None
        )
        
        if not technique:
            return f"Technique {technique_id} not found in MITRE ATT&CK database."
        
        name = technique.get("name", "Unknown")
        description = technique.get("description", "No description available.")
        platforms = ", ".join(technique.get("x_mitre_platforms", []))
        detection = technique.get("x_mitre_detection", "No detection guidance available.")
        
        return f"""
Technique ID: {technique_id}
Name: {name}
Platforms: {platforms}
Description: {description}
Detection Guidance: {detection}
""".strip()
    
    except Exception as e:
        return f"Could not fetch technique details: {str(e)}"