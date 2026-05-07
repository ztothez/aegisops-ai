import { RunResult, Scores } from "../types/aegis";

const API = "http://localhost:8000";

function dl(filename: string, content: string) {
  const a = document.createElement("a");
  a.href = "data:text/plain;charset=utf-8," + encodeURIComponent(content);
  a.download = filename; a.click();
}

export function PanelEyebrow({ dot, color, label, meta }: { dot: string; color: string; label: string; meta?: string }) {
  return (
    <div className="flex items-center gap-2 font-sans font-bold text-[11px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim mb-[13px]">
      <span className="w-[7px] h-[7px] rounded-full shrink-0" style={{ background: dot, boxShadow: `0 0 6px ${color}` }} />
      {label}
      {meta && <span className="ml-auto font-mono font-medium text-[11px] leading-none text-aegis-fg-faint tracking-[0.04em] normal-case">{meta}</span>}
    </div>
  );
}

export function MetaRow({ k, v, vc = "text-aegis-fg-2" }: { k: string; v: string; vc?: string }) {
  return (
    <div className="flex justify-between items-center bg-aegis-panel/60 border border-aegis-border rounded-md px-3.5 py-2 mb-[7px]">
      <span className="font-sans font-semibold text-xs leading-none text-aegis-fg-dim">{k}</span>
      <span className={`font-mono font-semibold text-xs leading-none tracking-[0.02em] ${vc}`}>{v}</span>
    </div>
  );
}

export function GateBadge({ v, colorClass, bgClass, borderClass }: { v: string; colorClass: string; bgClass: string; borderClass: string }) {
  return <span className={`font-mono font-bold text-[9px] leading-none tracking-[0.08em] uppercase px-[9px] py-1 rounded-[4px] border ${bgClass} ${borderClass} ${colorClass}`}>{v}</span>;
}

export function ScoreBox({ label, val, colorClass }: { label: string; val: string; colorClass: string }) {
  return (
    <div className="bg-aegis-input border border-aegis-border rounded-lg p-4 text-center">
      <div className={`font-mono font-bold text-[32px] leading-none mb-2 ${colorClass}`}>{val}</div>
      <div className="font-sans font-bold text-[9px] leading-none text-aegis-fg-faint tracking-[0.1em] uppercase">{label}</div>
    </div>
  );
}

export function ArtifactGrid({ results, technique }: { results: RunResult; technique: string }) {
  const tid = technique.split("·")[0].trim();
  const cards = [
    { label: "SIGMA YAML", desc: `Detection rule for ${tid}`, top: "border-t-aegis-blue", text: "text-aegis-blue-soft", content: results.artifacts.sigma, filename: `sigma_${tid}.yml` },
    { label: "SPLUNK SPL", desc: "Hunting query · index=wineventlog", top: "border-t-aegis-amber", text: "text-aegis-amber-soft", content: results.artifacts.splunk, filename: `splunk_${tid}.spl` },
    { label: "SOC PLAYBOOK", desc: "Triage · contain · escalate", top: "border-t-aegis-green", text: "text-aegis-green-soft", content: results.outputs.response, filename: `playbook_${tid}.md` },
    { label: "VECTR EXPORT", desc: "Navigator-style coverage JSON", top: "border-t-aegis-purple", text: "text-aegis-purple-soft", content: JSON.stringify({ technique, scores: results.scores, outputs: results.outputs }, null, 2), filename: `vectr_${tid}.json` },
    { label: "VALIDATION", desc: `Coverage ${results.scores.coverage}% · Safety ${results.scores.safety_verdict}`, top: "border-t-aegis-red", text: "text-aegis-red-soft", content: results.outputs.verifier, filename: `validation_${tid}.json` },
    { label: "PDF REPORT", desc: "SOC handoff bundle", top: "border-t-aegis-fg-muted", text: "text-aegis-fg-muted", content: null, filename: `aegisops_${tid}.pdf` },
  ];

  return (
    <div className="grid grid-cols-3 gap-2.5">
      {cards.map((art, i) => (
        <div key={i} className={`bg-aegis-panel-3 border border-aegis-border-hi border-t-2 ${art.top} rounded-lg px-[14px] py-3 h-[120px] flex flex-col justify-between`}>
          <div>
            <div className={`font-sans font-bold text-[10px] leading-none uppercase tracking-[0.12em] ${art.text}`}>{art.label}</div>
            <div className="font-sans font-normal text-xs leading-relaxed text-aegis-fg-muted mt-1.5">{art.desc}</div>
          </div>
          <button onClick={async () => {
            if (art.label === "PDF REPORT") {
              const r = await fetch(`${API}/export/pdf`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ technique_id: tid, red_output: results.outputs.red, blue_output: results.outputs.blue }) });
              const blob = await r.blob();
              const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = art.filename; a.click();
            } else dl(art.filename, art.content ?? "");
          }} className="self-start font-sans font-semibold text-[10px] leading-none uppercase tracking-[0.08em] text-aegis-green border border-aegis-border-green bg-aegis-tint-green px-2.5 py-1.5 rounded cursor-pointer hover:bg-aegis-green/20 transition-colors">
            ↓ {art.label.split(" ")[0]}
          </button>
        </div>
      ))}
    </div>
  );
}