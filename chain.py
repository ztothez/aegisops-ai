from mitre import load_mitre
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Common technique chains based on MITRE ATT&CK patterns
TECHNIQUE_CHAINS = {
    "T1059.001": ["T1053.005", "T1071.001"],  # PowerShell → Scheduled Task → Web Protocol C2
    "T1053.005": ["T1547.001", "T1078"],       # Scheduled Task → Registry Run Keys → Valid Accounts
    "T1078": ["T1021.001", "T1003.001"],        # Valid Accounts → RDP → LSASS Memory
    "T1003.001": ["T1550.002", "T1021.002"],    # LSASS → Pass the Hash → SMB
    "T1071.001": ["T1041", "T1048"],            # Web C2 → Exfil over C2 → Exfil Alt Protocol
    "T1547.001": ["T1112", "T1070.001"],        # Registry Run → Modify Registry → Clear Logs
    "T1021.001": ["T1057", "T1083"],            # RDP → Process Discovery → File Discovery
    "T1566.001": ["T1204.002", "T1059.001"],    # Spearphishing → Malicious File → PowerShell
    "T1190": ["T1059.004", "T1505.003"],        # Exploit Public App → Unix Shell → Web Shell
}

def get_next_techniques(technique_id: str) -> list[dict]:
    """Get suggested next techniques in the kill chain."""
    next_ids = TECHNIQUE_CHAINS.get(technique_id, [])
    if not next_ids:
        return []
    
    mitre = load_mitre()  # cached
    techniques = mitre.get_techniques(include_subtechniques=True)
    
    results = []
    for tid in next_ids:
        technique = next(
            (t for t in techniques if any(
                ref.get("external_id") == tid 
                for ref in t.get("external_references", [])
            )),
            None
        )
        if technique:
            results.append({
                "technique_id": tid,
                "name": technique.get("name", ""),
                "tactic": technique.get("kill_chain_phases", [{}])[0].get("phase_name", "")
            })
    
    return results