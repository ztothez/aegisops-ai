"use client";
import { useState, useRef, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import { PanelEyebrow, MetaRow, GateBadge } from "../components/SharedUI";
import { RunStatus, SidebarView, RunResult, Health } from "../types/aegis";

const API = "";
function ts() { return new Date().toISOString().substring(11, 19) + "Z"; }

function dl(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

async function downloadPdf(run: RunResult, canonicalId?: string) {
  const id = canonicalId || run.technique_id;

  const r = await fetch(`${API}/export/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      technique_id: id,
      red_output: run.outputs?.red ?? run.artifacts?.raw_red ?? "",
      blue_output: run.outputs?.blue ?? run.artifacts?.raw_blue ?? "",
      response_output: run.outputs?.response ?? "",
      verifier_output: run.outputs?.verifier ?? "",
      scores: run.scores,
      artifacts: run.artifacts,
      verifier_model: run.verifier_model,
      verifier_model_role: run.verifier_model_role,
    }),
  });

  if (!r.ok) {
    console.error("PDF export failed", r.status, await r.text());
    return;
  }

  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `aegisops_${id}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}


export default function SOCCommandCenter() {
  // Shared App State
  const [technique, setTechnique] = useState("T1059.001");
  const [mode, setMode] = useState("Single Technique");
  const [demoMode, setDemoMode] = useState(true);
  const [status, setStatus] = useState<RunStatus>("idle");
  const [logs, setLogs] = useState<string[]>([]);
  const [results, setResults] = useState<RunResult | null>(null);
  const [runHistory, setRunHistory] = useState<RunResult[]>([]);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [agentTimes, setAgentTimes] = useState<Record<string, string>>({});
  const [activeView, setActiveView] = useState<SidebarView>("overview");
  const [health, setHealth] = useState<Health | null>(null);

  // View-specific state
  const [threatSearch, setThreatSearch] = useState("");
  const [intelInput, setIntelInput] = useState("APT28");
  const [topoSeed, setTopoSeed] = useState("T1566.001");
  const [selectedPath, setSelectedPath] = useState(0);
  const [expandedAlert, setExpandedAlert] = useState<number | null>(null);
  const [expandedCase, setExpandedCase] = useState<number | null>(null);

  const logsRef = useRef<HTMLDivElement>(null);
  const agentStartRef = useRef<Record<string, number>>({});
  const collectedOutputs = useRef<Record<string, string>>({});

  useEffect(() => {
    logsRef.current?.scrollTo({ top: logsRef.current.scrollHeight, behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    fetch(`${API}/health`).then(r => r.json()).then(setHealth).catch(() => setHealth({ reachable: false }));
  }, []);

  const runPipeline = async (overrideMode?: string, overrideTarget?: string) => {
    if (status === "running") return;
    setStatus("running");

    const targetTechnique = overrideTarget || technique;
    const currentMode = overrideMode || mode;
    const tid = targetTechnique.split("·")[0].trim();

    setLogs([`${ts()} system online · pipeline_version=5.0`, `${ts()} mode=${currentMode} target=${tid}`]);
    setResults(null);
    setActiveAgent(null);
    setAgentTimes({});
    agentStartRef.current = {};
    collectedOutputs.current = {};

    try {
      const res = await fetch(`${API}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          technique_id: tid,
          demo: demoMode,
          mode: currentMode.toLowerCase().replace(/ /g, "_"),
        }),
      });
      if (!res.body) throw new Error("No stream");
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.trim()) continue;
          const ev = part.match(/event: (.*)/)?.[1]?.trim();
          const raw = part.match(/data: ([\s\S]*)/)?.[1]?.trim();
          if (!ev || !raw) continue;

          let data: any;
          try { data = JSON.parse(raw); } catch { continue; }

          // ── SSE event handlers ──────────────────────────────────────────
          if (ev === "agent_start") {
            agentStartRef.current[data.agent] = Date.now();
            setActiveAgent(data.agent);
            setLogs(p => [...p, `${ts()} ${data.agent}_agent ready · route=${data.agent === "verifier" ? "qwen_validator" : "primary_generator"}`]);

          } else if (ev === "agent_done") {
            const ms = agentStartRef.current[data.agent];
            const elapsed = ms ? ((Date.now() - ms) / 1000).toFixed(1) + "s" : "";
            setAgentTimes(p => ({ ...p, [data.agent]: elapsed }));
            collectedOutputs.current[data.agent] = data.output ?? "";
            setLogs(p => [...p, `${ts()} ${data.agent}_agent task complete`]);

          } else if (ev === "technique_done") {
            // Multi-technique progress — fires for each technique in Kill Chain / APT mode
            // Does NOT stop the pipeline; just logs progress
            setLogs(p => [...p, `${ts()} technique complete · ${data.technique_id} · ${data.index + 1}/${data.total}`]);

          } else if (ev === "done") {
            // Single final event — always fires exactly once at the end
            const outputs = {
              red: collectedOutputs.current["red"] ?? "",
              blue: collectedOutputs.current["blue"] ?? "",
              response: collectedOutputs.current["response"] ?? "",
              verifier: collectedOutputs.current["verifier"] ?? "",
            };
            const run: RunResult = {
              ...(data as any),
              outputs,
              technique_id: tid,
              mode: currentMode,
              timestamp: Date.now(),
            };
            setResults(run);
            setRunHistory(h => [run, ...h.slice(0, 19)]);
            setLogs(p => [...p,
              `${ts()} exports ready · Sigma · SPL · VECTR · JSON`,
              `${ts()} VALIDATED · ${run.scores.safety_verdict} · coverage=${run.scores.coverage}%`,
            ]);
            setStatus("success");
            setActiveAgent(null);
          }
          // ── end SSE handlers ────────────────────────────────────────────
        }
      }
    } catch (e: any) {
      setStatus("error");
      setLogs(p => [...p, `${ts()} CRITICAL: ${e.message}`]);
    }
  };

  const endpointOk = health?.reachable ?? false;
  const latencyLine = endpointOk ? `${health!.latency_ms} ms · /v1/models` : "configured · probe in dashboard";
  const modelName = health?.model?.split("/").pop()?.toUpperCase() ?? "LLAMA 3.3 70B";

  const heroPillClass = endpointOk
    ? "bg-aegis-tint-green border-aegis-border-green text-aegis-green"
    : "bg-aegis-tint-amber border-aegis-border-amber text-aegis-amber";
  const heroPillDot = endpointOk
    ? "bg-aegis-green shadow-[0_0_6px_#22C55E]"
    : "bg-aegis-amber shadow-[0_0_6px_#F59E0B]";
  const heroPillText = endpointOk
    ? `LIVE · VLLM ON ROCM · MI300X · ${modelName}`
    : "OFFLINE · DEMO FALLBACK ACTIVE";

  const verifierModel = results?.verifier_model ?? "";
  const verifierRole = results?.verifier_model_role ?? "";
  const qwenAudited =
    verifierModel.toLowerCase().includes("qwen") ||
    verifierRole.toLowerCase().includes("qwen");

  // ── Sub-Component: Artifact Grid ──────────────────────────────────────────
  const ArtifactGridComponent = ({ run }: { run: RunResult }) => {
    const isGroup = run.mode.toLowerCase() === "apt group";
    const canonicalId = isGroup
      ? (run.technique_id.includes("APT") ? run.technique_id : "APT_Run")
      : run.technique_id;

    const cards = [
      { label: "SIGMA YAML", desc: `Detection rule for ${canonicalId}`, top: "border-t-aegis-blue", text: "text-aegis-blue-soft", content: run.artifacts?.sigma || run.outputs.blue, filename: `sigma_${canonicalId}.yml` },
      { label: "SPLUNK SPL", desc: "Hunting query · index=windows", top: "border-t-aegis-amber", text: "text-aegis-amber-soft", content: run.artifacts?.splunk || run.outputs.red, filename: `splunk_${canonicalId}.spl` },
      { label: "SOC PLAYBOOK", desc: "Triage · contain · escalate", top: "border-t-aegis-green", text: "text-aegis-green-soft", content: run.outputs.response, filename: `playbook_${canonicalId}.md` },
      { label: "VECTR EXPORT", desc: "Navigator-style coverage JSON", top: "border-t-aegis-purple", text: "text-aegis-purple-soft", content: JSON.stringify({ technique: run.technique_id, scores: run.scores, mode: run.mode }, null, 2), filename: `vectr_${canonicalId}.json` },
      { label: "VALIDATION", desc: `Coverage ${run.scores.coverage}% · Safety ${run.scores.safety_verdict}`, top: "border-t-aegis-red", text: "text-aegis-red-soft", content: run.outputs.verifier, filename: `validation_${canonicalId}.json` },
      { label: "PDF REPORT", desc: "SOC handoff bundle", top: "border-t-aegis-fg-muted", text: "text-aegis-fg-muted", content: null, filename: `aegisops_${canonicalId}.pdf` },
    ];

    return (
      <div className="grid grid-cols-3 gap-2.5">
        {cards.map((art, i) => (
          <div key={i} className={`bg-aegis-panel-3 border border-aegis-border-hi border-t-2 ${art.top} rounded-lg px-[14px] py-3 h-[120px] flex flex-col justify-between`}>
            <div>
              <div className={`font-sans font-bold text-[10px] leading-none uppercase tracking-[0.12em] ${art.text}`}>{art.label}</div>
              <div className="font-sans font-normal text-xs leading-relaxed text-aegis-fg-muted mt-1.5">{art.desc}</div>
            </div>
            <button
              onClick={async () => {
                if (art.label === "PDF REPORT") {
                  await downloadPdf(run, canonicalId);
                } else {
                  dl(art.filename, typeof art.content === "string" ? art.content : JSON.stringify(art.content));
                }
              }}
              className="self-start font-sans font-semibold text-[10px] leading-none uppercase tracking-[0.08em] text-aegis-green border border-aegis-border-green bg-aegis-tint-green px-2.5 py-1.5 rounded cursor-pointer hover:bg-aegis-green/20 transition-colors"
            >
              ↓ {art.label.split(" ")[0]}
            </button>
          </div>
        ))}
      </div>
    );
  };

  // ── Render: Alerts ────────────────────────────────────────────────────────
  const renderAlerts = () => (
    <div className="flex-1 px-[22px] py-[18px] pb-8 overflow-y-auto">
      <div className="font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-[18px]">◇ ALERTS — Pipeline Run History</div>
      {runHistory.length === 0 ? (
        <div className="text-aegis-border-hi font-mono font-normal text-[13px] leading-[1.6] mt-12 text-center">No pipeline runs yet. Run a technique from the Overview.</div>
      ) : (
        <div className="flex flex-col gap-3">
          {runHistory.map((run: RunResult, i: number) => {
            const isExpanded = expandedAlert === i;
            return (
              <div key={i} className="bg-aegis-panel-3 border border-aegis-border-hi border-l-[3px] rounded-lg transition-colors overflow-hidden" style={{ borderLeftColor: run.scores.verdict === "PASS" ? "#22C55E" : "#EF4444" }}>
                <div onClick={() => setExpandedAlert(isExpanded ? null : i)} className="px-4 py-3 cursor-pointer flex justify-between items-center hover:bg-aegis-panel-2">
                  <div>
                    <div className="font-mono font-bold text-[13px] leading-none text-aegis-fg">{run.technique_id}</div>
                    <div className="font-mono font-normal text-[11px] leading-none text-aegis-fg-dim mt-1.5">{run.mode} · {new Date(run.timestamp).toLocaleTimeString()}</div>
                  </div>
                  <div className="flex gap-2 items-center">
                    <span className="font-mono font-bold text-[10px] leading-none px-2 py-1.5 rounded bg-aegis-tint-green border border-aegis-border-green text-aegis-green-soft">coverage {run.scores.coverage}%</span>
                    <span className={`font-mono font-bold text-[10px] leading-none px-2 py-1.5 rounded border ${run.scores.verdict === "PASS" ? "bg-aegis-tint-green border-aegis-border-green text-aegis-green-soft" : "bg-aegis-tint-red border-aegis-border-red text-aegis-red-soft"}`}>{run.scores.verdict}</span>
                    <span className="text-aegis-fg-dim ml-2 font-mono text-xs w-4 text-center">{isExpanded ? "▲" : "▼"}</span>
                  </div>
                </div>
                {isExpanded && (
                  <div className="px-4 pb-4 pt-2 border-t border-aegis-border-hi bg-aegis-panel">
                    <div className="grid grid-cols-2 gap-4 mt-2">
                      <div>
                        <div className="font-sans font-bold text-[10px] text-aegis-red-soft uppercase tracking-[0.1em] mb-2 flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-aegis-red-soft" /> RED TEAM - OFFENSE
                        </div>
                        <div className="bg-aegis-terminal border border-aegis-border-hi rounded-md p-3 h-80 overflow-y-auto font-mono text-[11.5px] leading-relaxed text-slate-300 whitespace-pre-wrap">
                          {run.outputs.red || "No threat output recorded."}
                        </div>
                      </div>
                      <div>
                        <div className="font-sans font-bold text-[10px] text-aegis-blue-soft uppercase tracking-[0.1em] mb-2 flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-aegis-blue-soft" /> BLUE TEAM - DEFENSE
                        </div>
                        <div className="bg-aegis-terminal border border-aegis-border-hi rounded-md p-3 h-80 overflow-y-auto font-mono text-[11.5px] leading-relaxed text-slate-300 whitespace-pre-wrap">
                          {run.outputs.blue || "No detection output recorded."}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );

  // ── Render: Cases ─────────────────────────────────────────────────────────
  const renderCases = () => (
    <div className="flex-1 px-[22px] py-[18px] pb-8 overflow-y-auto">
      <div className="font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-[18px]">▣ CASES — Saved Investigation Cases</div>
      {runHistory.length === 0 ? (
        <div className="text-aegis-border-hi font-mono font-normal text-[13px] leading-[1.6] mt-12 text-center">No cases yet. Completed pipeline runs appear here as cases.</div>
      ) : (
        <div className="flex flex-col gap-3">
          {runHistory.map((run: RunResult, i: number) => {
            const isExpanded = expandedCase === i;
            return (
              <div key={i} className="bg-aegis-panel border border-aegis-border-grid border-t-2 border-t-aegis-purple rounded-lg overflow-hidden transition-colors">
                <div onClick={() => setExpandedCase(isExpanded ? null : i)} className="px-4 py-3.5 cursor-pointer hover:bg-aegis-panel-2 flex justify-between items-center">
                  <div>
                    <div className="font-mono font-bold text-[13px] leading-none text-aegis-purple-soft mb-1.5">{run.technique_id}</div>
                    <div className="font-mono font-normal text-[11px] leading-relaxed text-aegis-fg-dim">{run.mode}</div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="font-mono font-normal text-[10px] leading-none text-aegis-fg-faint mb-1.5">{new Date(run.timestamp).toLocaleString()}</div>
                      <div className="flex justify-end gap-1.5">
                        <span className="font-mono font-bold text-[9px] leading-none px-1.5 py-1 rounded bg-aegis-tint-green border border-aegis-border-green text-aegis-green-soft">{run.scores.coverage}%</span>
                        <span className="font-mono font-bold text-[9px] leading-none px-1.5 py-1 rounded bg-aegis-tint-purple border border-aegis-border-purple text-aegis-purple-soft">{run.scores.verdict}</span>
                      </div>
                    </div>
                    <span className="text-aegis-fg-dim font-mono text-xs w-4 text-center">{isExpanded ? "▲" : "▼"}</span>
                  </div>
                </div>
                {isExpanded && (
                  <div className="px-4 pb-4 pt-2 border-t border-aegis-border-hi bg-aegis-panel-3">
                    <div className="grid grid-cols-2 gap-4 mt-2">
                      <div>
                        <div className="font-sans font-bold text-[10px] text-aegis-amber-soft uppercase tracking-[0.1em] mb-2 flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-aegis-amber-soft" /> SOC RESPONSE GUIDANCE
                        </div>
                        <div className="bg-aegis-terminal border border-aegis-border-hi rounded-md p-3 h-64 overflow-y-auto font-mono text-[11.5px] leading-relaxed text-slate-300 whitespace-pre-wrap">
                          {run.outputs.response || "No response output recorded."}
                        </div>
                      </div>
                      <div>
                        <div className="font-sans font-bold text-[10px] text-aegis-purple-soft uppercase tracking-[0.1em] mb-2 flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-aegis-purple-soft" /> PIPELINE VALIDATION
                        </div>
                        <div className="bg-aegis-terminal border border-aegis-border-hi rounded-md p-3 h-64 overflow-y-auto font-mono text-[11.5px] leading-relaxed text-slate-300 whitespace-pre-wrap">
                          {run.outputs.verifier || "No validation output recorded."}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );

  // ── Render: Threats ───────────────────────────────────────────────────────
  const renderThreats = () => {
    const catalog = [
      { id: "T1059.001", name: "PowerShell", tactic: "Execution" },
      { id: "T1059.003", name: "Windows Command Shell", tactic: "Execution" },
      { id: "T1566.001", name: "Spearphishing Attachment", tactic: "Initial Access" },
      { id: "T1078", name: "Valid Accounts", tactic: "Defense Evasion" },
      { id: "T1003.001", name: "LSASS Memory", tactic: "Credential Access" },
      { id: "T1021.001", name: "Remote Desktop Protocol", tactic: "Lateral Movement" },
    ].filter(t => !threatSearch || t.id.toLowerCase().includes(threatSearch.toLowerCase()) || t.name.toLowerCase().includes(threatSearch.toLowerCase()));

    const tacticColors: Record<string, string> = {
      "Execution": "#EF4444",
      "Initial Access": "#F59E0B",
      "Credential Access": "#3B82F6",
      "Lateral Movement": "#22C55E",
      "Defense Evasion": "#C4B5FD",
    };

    return (
      <div className="flex-1 px-[22px] py-[18px] pb-8 overflow-y-auto">
        <div className="font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-[18px]">◎ THREATS — MITRE ATT&CK Technique Browser</div>
        <input
          value={threatSearch}
          onChange={e => setThreatSearch(e.target.value)}
          placeholder="Search technique ID, name, or tactic…"
          className="w-full bg-aegis-input border border-aegis-border-hi rounded-md px-3.5 py-2.5 text-aegis-fg font-mono text-[13px] outline-none mb-[18px]"
        />
        <div className="grid grid-cols-3 gap-2.5">
          {catalog.map((t, i) => (
            <div
              key={i}
              onClick={() => { setTechnique(t.id); setMode("Single Technique"); setActiveView("overview"); }}
              className="bg-aegis-panel-3 border border-aegis-border-hi border-t-2 rounded-lg px-3.5 py-3 cursor-pointer hover:bg-aegis-panel-2 transition-colors"
              style={{ borderTopColor: tacticColors[t.tactic] || "#475569" }}
            >
              <div className="font-mono font-bold text-xs leading-none" style={{ color: tacticColors[t.tactic] || "#94A3B8" }}>{t.id}</div>
              <div className="font-sans font-semibold text-[13px] leading-relaxed text-aegis-fg-2 mt-1">{t.name}</div>
              <div className="font-sans font-normal text-[10px] leading-none text-aegis-fg-dim mt-1 uppercase tracking-[0.1em]">{t.tactic}</div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // ── Render: Hunting (Topology Lab) ────────────────────────────────────────
  const renderHunting = () => {
    const ATTACK_PATHS = [
      {
        id: "phish", label: "Phishing to PowerShell to C2",
        summary: "User execution leads to PowerShell, persistence, and C2 telemetry.",
        seed_techniques: ["T1566.001", "T1204.002", "T1059.001"],
        hops: [
          { from: "attacker", to: "mail", technique_id: "T1566.001", technique_name: "Spearphishing Attachment", action: "Deliver attachment to user mailbox", command: "Attachment: invoice_<CAMPAIGN_ID>.docm", telemetry: ["Email gateway attachment hash", "Sender domain reputation", "User mailbox delivery event"], detection: "Attachment from low-reputation sender reaches targeted user.", response: "Quarantine message, preserve headers.", realtime_signal: "EmailAttachmentHash + SenderDomain + RecipientUser", reaction_seconds: 18 },
          { from: "mail", to: "workstation", technique_id: "T1204.002", technique_name: "Malicious File", action: "User opens attachment", command: "WINWORD.EXE opens <DOCUMENT>.docm", telemetry: ["Office process start", "Document open event", "MOTW metadata"], detection: "Office process opens macro-enabled file from external email.", response: "Collect document, process tree, user context.", realtime_signal: "ParentImage=OUTLOOK.EXE and Image=WINWORD.EXE", reaction_seconds: 25 },
          { from: "workstation", to: "file", technique_id: "T1059.001", technique_name: "PowerShell", action: "PowerShell executes encoded validation command", command: "powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand <BASE64>", telemetry: ["Windows 4688", "PowerShell 4104", "Sysmon Event ID 1"], detection: "Encoded PowerShell with bypass from Office lineage.", response: "Isolate workstation if not approved.", realtime_signal: "CommandLine contains -EncodedCommand and -ExecutionPolicy Bypass", reaction_seconds: 12 },
        ],
      },
      {
        id: "valid_acct", label: "Valid Account to Domain Credential Access",
        summary: "Compromised credentials enable remote access and credential dumping.",
        seed_techniques: ["T1078", "T1021.001", "T1003.001"],
        hops: [
          { from: "attacker", to: "identity", technique_id: "T1078", technique_name: "Valid Accounts", action: "Authenticate with compromised account", command: "LogonType=10 User=<USER>", telemetry: ["Windows 4624", "Impossible travel signal", "MFA context"], detection: "New remote logon from unusual source.", response: "Disable session, rotate password.", realtime_signal: "EventID=4624 and LogonType=10 and Risk=High", reaction_seconds: 20 },
          { from: "identity", to: "dc", technique_id: "T1003.001", technique_name: "LSASS Memory", action: "Attempt credential access on privileged host", command: "rundll32.exe comsvcs.dll MiniDump <PID> <PATH> full", telemetry: ["Sysmon Event ID 10", "Process access to LSASS"], detection: "Process requests suspicious access rights to LSASS.", response: "Terminate process, rotate impacted credentials.", realtime_signal: "TargetImage=lsass.exe and GrantedAccess suspicious", reaction_seconds: 8 },
        ],
      },
    ];

    const SANDBOX_ZONES = ["Internet", "Workstation", "Server", "Identity", "Domain Controller", "SIEM/EDR"];
    const SANDBOX_NODES = [
      { id: "attacker", label: "External Actor", zone: "Internet", ip: "203.0.113.20" },
      { id: "mail", label: "Mail Gateway", zone: "Internet", ip: "198.51.100.15" },
      { id: "workstation", label: "Finance Workstation", zone: "Workstation", ip: "10.0.10.24" },
      { id: "file", label: "File Server", zone: "Server", ip: "10.0.30.30" },
      { id: "identity", label: "Identity Provider", zone: "Identity", ip: "10.0.40.10" },
      { id: "dc", label: "Domain Controller", zone: "Domain Controller", ip: "10.0.40.20" },
      { id: "siem", label: "SIEM/EDR", zone: "SIEM/EDR", ip: "10.0.50.5" },
    ];

    const filteredPaths = ATTACK_PATHS.filter(p => p.seed_techniques.includes(topoSeed) || true);
    const path = filteredPaths[selectedPath] || filteredPaths[0];
    const activeNodes = new Set(path.hops.flatMap((h: any) => [h.from, h.to]));

    return (
      <div className="flex-1 px-[22px] py-[18px] pb-8 overflow-y-auto">
        <div className="font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-[18px]">⌁ HUNTING — Topology Lab</div>
        <div className="flex gap-3 mb-4 items-end">
          <div className="flex-1">
            <div className="font-sans font-bold text-[10px] leading-none text-aegis-fg-dim tracking-[0.12em] uppercase mb-1.5">Seed Technique</div>
            <input value={topoSeed} onChange={e => setTopoSeed(e.target.value)} className="w-full bg-aegis-input border border-aegis-border-hi rounded-md px-3.5 py-2.5 text-aegis-fg font-mono text-[13px] outline-none" />
          </div>
          <div className="flex-[2]">
            <div className="font-sans font-bold text-[10px] leading-none text-aegis-fg-dim tracking-[0.12em] uppercase mb-1.5">Attack Path</div>
            <select value={selectedPath} onChange={e => setSelectedPath(Number(e.target.value))} className="w-full bg-aegis-input border border-aegis-border-hi rounded-md px-3.5 py-2.5 text-aegis-fg font-mono text-[13px] outline-none">
              {filteredPaths.map((p: any, i: number) => <option key={i} value={i}>{p.label}</option>)}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-2.5 mb-4">
          {[
            { v: String(SANDBOX_NODES.length), l: "Sandbox Nodes", c: "text-aegis-purple" },
            { v: String(path.hops.length), l: "Attack Hops", c: "text-aegis-red" },
            { v: "100%", l: "Detection Coverage", c: "text-aegis-green" },
            { v: "~15s", l: "Avg Reaction", c: "text-aegis-amber" },
          ].map((m, i) => (
            <div key={i} className="bg-aegis-panel-2 border border-aegis-border-grid rounded-lg px-4 py-3 text-center">
              <div className={`font-mono font-bold text-[22px] leading-none ${m.c}`}>{m.v}</div>
              <div className="font-sans font-bold text-[9px] leading-none text-aegis-fg-faint tracking-[0.1em] uppercase mt-1.5">{m.l}</div>
            </div>
          ))}
        </div>
        <div className="bg-aegis-bg border border-aegis-border-hi rounded-xl p-[18px] mb-4">
          <div className="font-sans font-bold text-[10px] leading-none tracking-[0.14em] uppercase text-aegis-purple mb-1.5">SANDBOX TOPOLOGY</div>
          <div className="font-sans font-extrabold text-[18px] leading-none text-aegis-fg mb-1">{path.label}</div>
          <div className="font-sans font-normal text-[12px] leading-[1.55] text-aegis-fg-muted mb-3.5">{path.summary}</div>
          <div className="flex gap-2.5 flex-wrap">
            {SANDBOX_ZONES.map((zone: string) => {
              const nodes = SANDBOX_NODES.filter(n => n.zone === zone);
              if (!nodes.length) return null;
              return (
                <div key={zone} className="flex-1 min-w-[120px] bg-aegis-panel-3 border border-aegis-border rounded-lg p-3">
                  <div className="font-sans font-bold text-[9px] leading-none tracking-[0.12em] uppercase text-aegis-fg-dim mb-2.5">{zone}</div>
                  {nodes.map(node => {
                    const active = activeNodes.has(node.id);
                    return (
                      <div key={node.id} className={`rounded-[7px] px-3 py-2.5 mb-2 border ${active ? "bg-aegis-tint-red border-aegis-red" : "bg-aegis-input border-aegis-border-hi"}`}>
                        <div className={`font-sans font-bold text-[11px] leading-[1.35] ${active ? "text-aegis-red-soft" : "text-slate-300"}`}>{node.label}</div>
                        <div className="font-mono font-normal text-[10px] leading-none text-aegis-fg-dim mt-1.5">{node.ip}</div>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
        <div className="font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-3">▸ ATTACK TIMELINE</div>
        {path.hops.map((hop: any, i: number) => (
          <div key={i} className="bg-aegis-panel-3 border border-aegis-border-hi border-l-[3px] border-l-aegis-red rounded-lg px-4 py-3.5 mb-2.5">
            <div className="font-mono font-bold text-xs leading-none text-aegis-red-soft mb-2">Hop {i + 1}: {hop.technique_id} · {hop.technique_name}</div>
            <div className="font-sans font-normal text-xs leading-[1.6] text-slate-300 mb-2">{hop.action}</div>
            <div className="bg-aegis-terminal border border-aegis-border-hi rounded-md px-3 py-2 font-mono font-normal text-[11px] leading-none text-aegis-purple-soft mb-2">{hop.command}</div>
            <div className="flex flex-wrap gap-1 mb-2">
              {hop.telemetry.map((t: string, j: number) => <span key={j} className="bg-aegis-tint-blue border border-aegis-border-blue text-aegis-blue-soft font-mono font-normal text-[10px] leading-none px-2 py-1 rounded-[3px]">{t}</span>)}
            </div>
            <div className="font-sans font-normal text-xs leading-[1.55] text-aegis-blue-soft"><strong>Detection:</strong> {hop.detection}</div>
            <div className="font-sans font-normal text-xs leading-[1.55] text-aegis-green-soft mt-1"><strong>Response:</strong> {hop.response}</div>
            <div className="font-mono font-normal text-[11px] leading-none text-aegis-amber mt-2">Realtime: {hop.realtime_signal} · reacts in ~{hop.reaction_seconds}s</div>
          </div>
        ))}
      </div>
    );
  };

  // ── Render: Intel ─────────────────────────────────────────────────────────
  const renderIntel = () => (
    <div className="flex-1 px-[22px] py-[18px] pb-8 overflow-y-auto">
      <div className="font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-[18px]">◌ INTEL — APT Group Intelligence</div>
      <div className="flex gap-2.5 mb-[18px]">
        <input
          value={intelInput}
          onChange={e => setIntelInput(e.target.value)}
          placeholder="APT Group name, e.g. APT28"
          className="flex-1 bg-aegis-input border border-aegis-border-hi rounded-md px-3.5 py-2.5 text-aegis-fg font-mono text-[13px] outline-none"
        />
        <button
          onClick={() => {
            setMode("APT Group");
            setTechnique(intelInput);
            setActiveView("overview");
            runPipeline("APT Group", intelInput);
          }}
          className="px-5 rounded-md bg-gradient-to-br from-[#7C3AED] to-[#4F46E5] border border-aegis-purple/50 text-white font-sans font-bold text-[11px] leading-none tracking-[0.08em] uppercase cursor-pointer hover:shadow-aegis-hover transition-shadow"
        >
          Run APT Simulation
        </button>
      </div>
      <div className="bg-aegis-tint-purple border border-aegis-border-purple rounded-lg px-4 py-3 mb-[18px]">
        <div className="font-sans font-normal text-xs leading-relaxed text-aegis-purple-soft">APT Group mode runs the full pipeline against each of the group&apos;s top MITRE ATT&CK techniques. Results stream into the Alerts and Cases views.</div>
      </div>
    </div>
  );

  // ── Render: Reports ───────────────────────────────────────────────────────
  const renderReports = () => {
    if (runHistory.length === 0) {
      return (
        <div className="flex-1 px-[22px] py-[18px] pb-8 overflow-y-auto">
          <div className="font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-[18px]">▤ REPORTS — Pipeline Run Reports</div>
          <div className="text-aegis-border-hi font-mono font-normal text-[13px] leading-[1.6] mt-12 text-center">No reports generated yet. Run the pipeline to create a report.</div>
        </div>
      );
    }

    const latestRun = runHistory[0];
    const isGroup = latestRun.mode.toLowerCase() === "apt group";
    const canonicalId = isGroup
      ? (latestRun.technique_id.includes("APT") ? latestRun.technique_id : "APT_Run")
      : latestRun.technique_id;

    return (
      <div className="flex-1 px-[22px] py-[18px] pb-8 overflow-y-auto">
        <div className="font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-[18px]">▤ REPORTS — Pipeline Run Reports</div>
        <div className="bg-gradient-to-br from-aegis-panel-3 to-aegis-panel border border-aegis-border-purple rounded-xl p-6 mb-6 relative overflow-hidden">
          <div className="flex items-center gap-2 mb-4">
            <div className="font-sans font-bold text-[10px] leading-none text-aegis-purple-soft tracking-[0.14em] uppercase">▸ Latest Generated Report</div>
            {qwenAudited && (
              <div className="inline-flex items-center rounded border border-aegis-border-purple bg-aegis-tint-purple px-2 py-1 font-mono text-[9px] font-bold uppercase tracking-[0.08em] text-aegis-purple-soft">
                Audited by {verifierModel}
              </div>
            )}
          </div>
          <div className="flex justify-between items-start">
            <div>
              <div className="font-mono font-bold text-3xl text-aegis-fg mb-1">{latestRun.technique_id}</div>
              <div className="font-mono font-normal text-xs text-aegis-fg-dim mb-6">{latestRun.mode} · {new Date(latestRun.timestamp).toLocaleString()}</div>
              <div className="flex gap-4 mb-6">
                <div>
                  <div className="font-sans font-bold text-[9px] text-aegis-fg-faint uppercase tracking-[0.1em] mb-1">Coverage</div>
                  <div className={`font-mono font-bold text-xl ${latestRun.scores.coverage >= 80 ? "text-aegis-green" : "text-aegis-amber"}`}>{latestRun.scores.coverage}%</div>
                </div>
                <div>
                  <div className="font-sans font-bold text-[9px] text-aegis-fg-faint uppercase tracking-[0.1em] mb-1">Verdict</div>
                  <div className={`font-mono font-bold text-xl ${latestRun.scores.verdict === "PASS" ? "text-aegis-green" : "text-aegis-red"}`}>{latestRun.scores.verdict}</div>
                </div>
                <div>
                  <div className="font-sans font-bold text-[9px] text-aegis-fg-faint uppercase tracking-[0.1em] mb-1">Safety</div>
                  <div className="font-mono font-bold text-xl text-aegis-green">{latestRun.scores.safety_verdict || "PASS"}</div>
                </div>
              </div>
            </div>
            <button
              onClick={() => downloadPdf(latestRun, canonicalId)}
              className="mt-2 px-6 py-3 bg-gradient-to-br from-[#7C3AED] to-[#4F46E5] text-white rounded-lg font-sans text-xs font-bold uppercase tracking-[0.08em] hover:scale-[1.02] transition-transform"
            >
              ↓ Download PDF
            </button>
          </div>
        </div>
        {runHistory.length > 1 && (
          <div>
            <div className="font-sans font-bold text-[10px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-3">Previous Reports</div>
            {runHistory.slice(1).map((run: RunResult, i: number) => {
              const cid = run.mode.toLowerCase() === "apt group"
                ? (run.technique_id.includes("APT") ? run.technique_id : "APT_Run")
                : run.technique_id;
              return (
                <div key={i} className="bg-aegis-panel-2 border border-aegis-border-hi rounded-md px-4 py-3 mb-2 flex justify-between items-center hover:bg-aegis-panel transition-colors">
                  <div>
                    <div className="font-mono font-bold text-[13px] text-aegis-fg">{run.technique_id}</div>
                    <div className="font-mono font-normal text-[10px] text-aegis-fg-dim">{new Date(run.timestamp).toLocaleString()}</div>
                  </div>
                  <button
                    onClick={() => downloadPdf(run, cid)}
                    className="text-aegis-fg-muted hover:text-aegis-purple-soft font-sans text-[10px] font-bold uppercase tracking-[0.08em] transition-colors"
                  >
                    ↓ PDF
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  // ── Render: Exports ───────────────────────────────────────────────────────
  const renderExports = () => (
    <div className="flex-1 px-[22px] py-[18px] pb-8 overflow-y-auto">
      <div className="font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-[18px]">⚙ EXPORTS — Deployable Artifacts</div>
      {!results ? (
        <div className="text-aegis-border-hi font-mono font-normal text-[13px] leading-[1.6] mt-12 text-center">
          Run the pipeline from Overview to generate export artifacts.<br />
          <button onClick={() => setActiveView("overview")} className="mt-4 px-5 py-2 border border-aegis-border-purple bg-aegis-tint-purple text-aegis-purple-soft rounded-md font-sans font-bold text-[10px] leading-none tracking-[0.1em] uppercase cursor-pointer">← Back to Command Center</button>
        </div>
      ) : <ArtifactGridComponent run={results} />}
    </div>
  );

  // ── Render: Overview (main dashboard) ─────────────────────────────────────
  const renderOverview = () => (
    <div className="flex-1 px-[22px] py-[18px] pb-8 flex flex-col gap-[18px] overflow-y-auto min-w-0">
      {/* HERO */}
      <section className="relative bg-aegis-panel border border-aegis-border-purple rounded-lg px-[22px] py-[18px] overflow-hidden min-h-[190px]">
        <div className="absolute inset-0 opacity-45 pointer-events-none" style={{ backgroundImage: "linear-gradient(45deg,rgba(139,92,246,0.05) 25%,transparent 25%,transparent 75%,rgba(139,92,246,0.05) 75%),linear-gradient(45deg,rgba(139,92,246,0.05) 25%,transparent 25%,transparent 75%,rgba(139,92,246,0.05) 75%)", backgroundSize: "24px 24px", backgroundPosition: "0 0,12px 12px", maskImage: "radial-gradient(ellipse at right,black 0%,transparent 70%)" }} />
        <div className="relative flex justify-between items-start gap-6">
          <div>
            <h1 className="m-0 font-sans font-bold text-[68px] leading-none tracking-[-0.03em] text-aegis-fg">
              AegisOps <span className="text-aegis-purple">AI</span>
            </h1>
            <div className="mt-2.5 font-sans font-normal text-[15px] leading-snug text-aegis-fg-muted">
              PURPLE TEAMING & SOC READINESS · MITRE TO DETECTION COPILOT
            </div>
            <div className="flex flex-wrap gap-2 mt-[18px]">
              {[
                { l: "MITRE ATT&CK v14", bg: "bg-aegis-tint-red", bd: "border-aegis-border-red", c: "text-aegis-red-soft" },
                { l: "LangGraph", bg: "bg-aegis-tint-blue", bd: "border-aegis-border-blue", c: "text-aegis-blue-soft" },
                { l: "vLLM on ROCm", bg: "bg-aegis-tint-amber", bd: "border-aegis-border-amber", c: "text-aegis-amber-soft" },
                { l: "AMD MI300X", bg: "bg-aegis-tint-green", bd: "border-aegis-border-green", c: "text-aegis-green-soft" },
                { l: "Qwen Validator", bg: "bg-aegis-tint-purple", bd: "border-aegis-border-purple", c: "text-aegis-purple-soft" },
              ].map((p, i) => (
                <span key={i} className={`inline-flex items-center h-[34px] px-3.5 rounded-md border ${p.bd} ${p.bg} font-mono font-bold text-xs tracking-[0.04em] ${p.c}`}>&gt;_ {p.l}</span>
              ))}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2.5 shrink-0">
            <div className="bg-aegis-panel border border-slate-400/55 rounded-md px-[18px] py-[11px] font-sans font-bold text-[13px] leading-none tracking-[0.12em] uppercase text-slate-300">
              AMD DEVELOPER HACKATHON 2026
            </div>
            <div className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full font-sans font-bold text-[10px] leading-none tracking-[0.1em] uppercase border ${heroPillClass}`}>
              <span className={`w-1.5 h-1.5 rounded-full inline-block ${heroPillDot} ${endpointOk ? "animate-aegis-blink" : ""}`} />
              {heroPillText}
            </div>
          </div>
        </div>
      </section>

      {/* SYSTEM STATUS */}
      <section className="bg-gradient-to-b from-aegis-panel-2 to-aegis-panel border border-aegis-border-grid rounded-lg px-[22px] py-3.5 flex flex-col gap-2.5">
        <div className="font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim">▸ SYSTEM STATUS</div>
        <div className="flex flex-wrap gap-y-3 gap-x-6">
          {[
            { dot: endpointOk ? "bg-aegis-green shadow-[0_0_6px_#22C55E]" : "bg-aegis-amber shadow-[0_0_6px_#F59E0B]", blink: endpointOk, text: endpointOk ? "AMD MI300X ENDPOINT: LIVE / DEMO READY" : "AMD MI300X ENDPOINT: DEMO FALLBACK ACTIVE" },
            { dot: "bg-aegis-purple shadow-[0_0_6px_#8B5CF6]", blink: false, text: `PRIMARY: ${modelName}` },
            { dot: "bg-aegis-purple shadow-[0_0_6px_#8B5CF6]", blink: false, text: "VALIDATOR: QWEN/QWQ" },
            { dot: "bg-aegis-blue shadow-[0_0_6px_#3B82F6]", blink: false, text: "MODE: HYBRID" },
            { dot: "bg-aegis-green shadow-[0_0_6px_#22C55E]", blink: false, text: `SAFETY: ${results?.scores.safety_verdict ?? "PASS"}` },
          ].map((s, i) => (
            <span key={i} className="inline-flex items-center gap-2 font-mono font-medium text-[11px] leading-none text-aegis-fg-2 tracking-[0.05em] uppercase shrink-0">
              <span className={`w-[7px] h-[7px] rounded-full inline-block ${s.dot} ${s.blink ? "animate-aegis-blink" : ""}`} />
              {s.text}
            </span>
          ))}
        </div>
      </section>

      {/* MISSION INPUT & META */}
      <div className="grid grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] gap-[18px]">
        <div className="bg-gradient-to-b from-aegis-panel-2 to-aegis-panel border border-aegis-border-grid rounded-lg px-5 py-[18px]">
          <PanelEyebrow dot="#8B5CF6" color="#8B5CF6" label="MISSION INPUT" meta="technique · group · chain · topology" />
          <div className="bg-aegis-bg-deep border border-aegis-border-hi rounded-md px-3.5 py-2.5 flex items-center gap-2 mb-3">
            <span className="text-aegis-purple font-mono font-bold text-sm shrink-0">&gt;_</span>
            <input
              value={technique}
              onChange={e => setTechnique(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") runPipeline(); }}
              disabled={status === "running"}
              placeholder="T1059.001 · PowerShell · Enterprise Workstation → SIEM Detection"
              className="flex-1 bg-transparent border-none outline-none text-aegis-fg font-mono font-medium text-[13px] placeholder:text-aegis-fg-faint"
            />
            <span className="w-2 h-4 bg-aegis-purple animate-aegis-blink-fast inline-block shrink-0" />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <label className="flex items-center gap-2 font-sans font-medium text-[11px] text-aegis-fg-dim cursor-pointer select-none">
              <div onClick={() => setDemoMode((d: boolean) => !d)} className={`w-[36px] h-[20px] rounded-full relative cursor-pointer transition-colors duration-200 ${demoMode ? "bg-aegis-purple/50" : "bg-aegis-border-hi"}`}>
                <div className={`absolute top-[3px] w-[14px] h-[14px] rounded-full transition-all duration-200 ${demoMode ? "bg-aegis-purple-soft left-[19px]" : "bg-aegis-fg-faint left-[3px]"}`} />
              </div>
              Demo
            </label>
            {["Single Technique", "APT Group", "Kill Chain", "Topology Lab"].map(m => (
              <button key={m} onClick={() => setMode(m)} className={`px-3 py-1.5 rounded-md font-sans font-bold text-[10px] leading-none tracking-[0.08em] uppercase cursor-pointer transition-all duration-120 ${mode === m ? "border border-aegis-border-purple bg-aegis-tint-purple text-aegis-purple-soft" : "border border-aegis-border bg-transparent text-aegis-fg-faint hover:text-aegis-fg-muted"}`}>
                {m}
              </button>
            ))}
            <button onClick={() => runPipeline()} disabled={status === "running"} className="ml-auto h-8 px-[18px] rounded-md font-sans font-bold text-[11px] leading-none tracking-[0.08em] uppercase text-white bg-gradient-to-br from-[#7C3AED] to-[#4F46E5] border border-aegis-purple/50 cursor-pointer disabled:opacity-50 hover:shadow-aegis-hover transition-shadow">
              {status === "running" ? "Running…" : "Run Pipeline →"}
            </button>
          </div>
        </div>
        <div className="bg-gradient-to-b from-aegis-panel-2 to-aegis-panel border border-aegis-border-grid rounded-lg px-5 py-[18px]">
          <PanelEyebrow dot="#3B82F6" color="#3B82F6" label="PIPELINE META" meta="v5.0 · hybrid" />
          <MetaRow k="Status" v={status === "running" ? "RUNNING" : status === "success" ? "COMPLETE" : "READY"} vc={status === "running" ? "text-aegis-amber" : "text-aegis-green"} />
          <MetaRow k="Workflow" v={mode} />
          <MetaRow k="Artifacts" v="Sigma · SPL · VECTR · JSON" vc="text-aegis-fg-muted" />
          <MetaRow k="Validation" v="Qwen Validator" vc="text-aegis-purple-soft" />
        </div>
      </div>

      {/* MONITOR & GATES */}
      <div className="grid grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] gap-[18px]">
        <div className="bg-aegis-terminal border border-aegis-border-hi rounded-lg px-[18px] py-4 flex flex-col min-h-[240px]">
          <div className="flex justify-between items-center mb-2.5">
            <span className="font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-[18px]">▸ LIVE MONITOR</span>
            <div className="flex items-center gap-2 font-mono font-medium text-[11px] text-aegis-fg-faint">
              <span className="w-[7px] h-[7px] rounded-full bg-aegis-green shadow-[0_0_6px_#22C55E] inline-block animate-[aegis-blink_1.4s_infinite]" />
              {status === "running" ? "STREAMING" : "IDLE"} · {logs.length} events
            </div>
          </div>
          <div ref={logsRef} className="flex-1 overflow-y-auto flex flex-col gap-1">
            {logs.map((line: string, i: number) => {
              const sep = line.indexOf("Z ") + 2;
              const t = line.substring(0, sep - 1);
              const rest = line.substring(sep);
              return (
                <div key={i} className="font-mono font-normal text-[11.5px] leading-[1.5]">
                  <span className="text-aegis-fg-faint mr-2.5">{t}</span>
                  <span className={`${line.includes("VALIDATED") ? "text-aegis-green-soft font-bold" : line.includes("ERROR") || line.includes("CRITICAL") ? "text-aegis-red-soft" : line.includes("ready") ? "text-aegis-purple-soft" : "text-aegis-fg-muted"}`}>{rest}</span>
                </div>
              );
            })}
          </div>
        </div>
        <div className="bg-gradient-to-b from-aegis-panel-2 to-aegis-panel border border-aegis-border-grid rounded-lg px-5 py-[18px]">
          <PanelEyebrow dot="#22C55E" color="#22C55E" label="READINESS GATES" meta={results ? "6 / 6 ready" : "0 / 6 ready"} />
          <div className="grid grid-cols-2 gap-2">
            {[
              { k: "Coverage Gate", v: results ? "READY" : "PENDING", bg: results ? "bg-aegis-tint-green" : "bg-slate-500/10", bd: results ? "border-aegis-border-green" : "border-slate-500/30", c: results ? "text-aegis-green-soft" : "text-aegis-fg-dim" },
              { k: "Safety Gate", v: results ? (results.scores.safety_verdict || "PASS") : "WAITING", bg: results ? "bg-aegis-tint-green" : "bg-slate-500/10", bd: results ? "border-aegis-border-green" : "border-slate-500/30", c: results ? "text-aegis-green-soft" : "text-aegis-fg-dim" },
              { k: "Product Readiness", v: results ? "ENABLED" : "LOCKED", bg: results ? "bg-aegis-tint-purple" : "bg-slate-500/10", bd: results ? "border-aegis-border-purple" : "border-slate-500/30", c: results ? "text-aegis-purple-soft" : "text-aegis-fg-dim" },
              { k: "Demo Fallback", v: "AVAILABLE", bg: "bg-aegis-tint-amber", bd: "border-aegis-border-amber", c: "text-aegis-amber-soft" },
              { k: "Qwen Validator", v: "CONFIGURED", bg: "bg-aegis-tint-purple", bd: "border-aegis-border-purple", c: "text-aegis-purple-soft" },
              { k: "Artifact Export", v: results ? "READY" : "PENDING", bg: results ? "bg-aegis-tint-green" : "bg-slate-500/10", bd: results ? "border-aegis-border-green" : "border-slate-500/30", c: results ? "text-aegis-green-soft" : "text-aegis-fg-dim" },
            ].map((g, i) => (
              <div key={i} className="flex justify-between items-center bg-slate-800/50 border border-aegis-border rounded-md px-3 py-2">
                <span className="font-sans font-semibold text-[11px] leading-none text-aegis-fg-muted">{g.k}</span>
                <GateBadge v={g.v} colorClass={g.c} bgClass={g.bg} borderClass={g.bd} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* AGENTS */}
      <div className="grid grid-cols-[1fr_1fr_1fr_1.18fr] gap-3.5">
        {[
          { id: "red", label: "Threat Agent", model: "Llama 3.3 70B", top: "border-t-aegis-purple", text: "text-aegis-purple-soft", route: "primary" },
          { id: "blue", label: "Detection Agent", model: "Llama 3.3 70B", top: "border-t-aegis-blue", text: "text-aegis-blue-soft", route: "primary" },
          { id: "response", label: "Response Agent", model: "Llama 3.3 70B", top: "border-t-aegis-amber", text: "text-aegis-amber-soft", route: "primary" },
          { id: "verifier", label: "Validation Agent", model: qwenAudited ? verifierModel : "Qwen-ready Validator", top: "border-t-aegis-purple", text: "text-aegis-purple-soft", route: qwenAudited ? "qwen_validator" : "validator_ready" },
        ].map((agent, i) => {
          const isRunning = activeAgent === agent.id;
          const elapsed = agentTimes[agent.id];
          const isDone = !!elapsed;
          return (
            <div key={i} className={`relative bg-aegis-panel-2 border border-aegis-border-hi border-t-2 ${agent.top} rounded-lg px-3.5 py-2.5 h-20 flex flex-col justify-between`}>
              <div>
                <div className={`font-sans font-bold text-xs leading-none ${agent.text}`}>{agent.label}</div>
                <div className="font-sans font-normal text-xs leading-none text-aegis-fg mt-1">{agent.model}</div>
              </div>
              <div className={`font-mono font-normal text-[11px] leading-none ${isRunning ? "text-aegis-amber-soft" : "text-aegis-fg-dim"}`}>
                {isDone ? `completed · ${agent.route} · ${elapsed}` : isRunning ? "analyzing target…" : "awaiting execution…"}
              </div>
              {isDone && <div className="absolute right-3 top-1/2 -translate-y-1/2 w-[18px] h-[18px] rounded-full bg-aegis-tint-green border border-aegis-border-green text-aegis-green font-sans font-bold text-[10px] leading-[18px] text-center">✓</div>}
              {i < 3 && <div className="absolute -right-2.5 top-1/2 -translate-y-1/2 translate-x-1/2 text-aegis-border-hi font-mono text-sm pointer-events-none">→</div>}
            </div>
          );
        })}
      </div>

      {results && (
        <section>
          <div className="font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-3">▸ DEPLOYABLE ARTIFACTS</div>
          <ArtifactGridComponent run={results} />
        </section>
      )}
    </div>
  );

  return (
    <div className="flex min-h-screen bg-aegis-bg-deep text-aegis-fg font-sans">
      <Sidebar activeView={activeView} setActiveView={setActiveView} latencyLine={latencyLine} endpointOk={endpointOk} />
      {activeView === "overview" && renderOverview()}
      {activeView === "alerts" && renderAlerts()}
      {activeView === "cases" && renderCases()}
      {activeView === "threats" && renderThreats()}
      {activeView === "hunting" && renderHunting()}
      {activeView === "intel" && renderIntel()}
      {activeView === "reports" && renderReports()}
      {activeView === "exports" && renderExports()}
    </div>
  );
}