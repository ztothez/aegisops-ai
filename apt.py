import os
from mitre import load_mitre

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_apt_techniques(group_name: str) -> list[dict]:
    mitre = load_mitre()  # cached
    groups = mitre.get_groups()
    
    # Find group by name (case insensitive)
    target_group = next(
        (g for g in groups if group_name.lower() in g.get("name", "").lower() or
         any(group_name.lower() in alias.lower() 
             for alias in g.get("aliases", []))),
        None
    )
    
    if not target_group:
        return []
    
    group_id = target_group.get("id")
    techniques_used = mitre.get_techniques_used_by_group(group_id)
    
    results = []
    for item in techniques_used[:5]:  # limit to 5 techniques for demo
        technique = item.get("object")
        if not technique:
            continue
        ext_refs = technique.get("external_references", [])
        technique_id = next(
            (r.get("external_id") for r in ext_refs if r.get("source_name") == "mitre-attack"),
            None
        )
        if technique_id:
            results.append({
                "technique_id": technique_id,
                "name": technique.get("name", ""),
                "tactic": technique.get("kill_chain_phases", [{}])[0].get("phase_name", "")
            })
    
    return results


def get_group_info(group_name: str) -> dict:
    mitre = load_mitre()  # cached
    groups = mitre.get_groups()
    
    target_group = next(
        (g for g in groups if group_name.lower() in g.get("name", "").lower() or
         any(group_name.lower() in alias.lower() 
             for alias in g.get("aliases", []))),
        None
    )
    
    if not target_group:
        return {}
    
    return {
        "name": target_group.get("name", ""),
        "aliases": target_group.get("aliases", []),
        "description": target_group.get("description", "")[:500]
    }