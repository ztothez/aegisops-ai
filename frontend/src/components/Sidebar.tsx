import { SidebarView } from "../types/aegis";

interface SidebarProps {
  activeView: SidebarView;
  setActiveView: (v: SidebarView) => void;
  latencyLine: string;
  endpointOk: boolean;
}

export default function Sidebar({ activeView, setActiveView, latencyLine, endpointOk }: SidebarProps) {
  const items = [
    { g: "◈", l: "OVERVIEW", v: "overview" as SidebarView },
    { g: "◇", l: "ALERTS", v: "alerts" as SidebarView },
    { g: "▣", l: "CASES", v: "cases" as SidebarView },
    { g: "◎", l: "THREATS", v: "threats" as SidebarView },
    { g: "⌁", l: "HUNTING", v: "hunting" as SidebarView },
    { g: "◌", l: "INTEL", v: "intel" as SidebarView },
    { g: "▤", l: "REPORTS", v: "reports" as SidebarView },
    { g: "⚙", l: "EXPORTS", v: "exports" as SidebarView },
  ];

  return (
    <aside className="w-[224px] bg-aegis-bg border-r border-aegis-border py-[18px] px-3.5 flex flex-col gap-3.5 sticky top-0 h-screen overflow-y-auto shrink-0">
      <div className="flex items-center gap-[9px] pb-3 border-b border-aegis-border">
        <div className="w-7 h-7 rounded-md bg-gradient-to-br from-aegis-purple to-aegis-red flex items-center justify-center font-sans font-extrabold text-[14px] leading-none text-white shrink-0">
          A
        </div>
        <div>
          <div className="font-sans font-bold text-[14px] leading-none text-aegis-fg tracking-tight">
            AegisOps <span className="text-aegis-purple">AI</span>
          </div>
          <div className="font-sans font-medium text-[9px] leading-none text-aegis-fg-dim tracking-[0.14em] uppercase mt-[3px]">
            SOC OPERATOR
          </div>
        </div>
      </div>

      <div className="font-sans font-bold text-[10px] leading-none text-aegis-fg-muted tracking-[0.14em] uppercase px-2">
        SOC Console
      </div>

      <nav className="flex flex-col gap-[3px]">
        {items.map((item) => (
          <div
            key={item.v}
            onClick={() => setActiveView(item.v)}
            className={`flex items-center gap-[9px] px-2.5 py-2 rounded-md border cursor-pointer transition-all duration-150 font-sans font-medium text-[12.5px] leading-none ${
              activeView === item.v
                ? "bg-aegis-tint-purple border-aegis-purple/40 text-aegis-purple-soft"
                : "border-transparent bg-transparent text-aegis-fg-muted hover:text-aegis-fg hover:bg-aegis-input"
            }`}
          >
            <span className={`w-[14px] text-center font-mono font-normal text-[14px] leading-none ${activeView === item.v ? "text-aegis-purple-soft" : "text-aegis-fg-dim"}`}>
              {item.g}
            </span>
            {item.l}
          </div>
        ))}
      </nav>

      <div className="mt-auto p-2.5 bg-aegis-input border border-aegis-border rounded-md flex flex-col gap-1.5">
        <div className="font-sans font-bold text-[9px] leading-none tracking-[0.14em] uppercase text-aegis-fg-dim">
          Endpoint
        </div>
        <div className="font-mono font-medium text-[11px] leading-[1.4] text-aegis-fg-2">
          vLLM · MI300X
        </div>
        <div className={`font-mono font-medium text-[10px] leading-[1.4] ${endpointOk ? "text-aegis-green-soft" : "text-aegis-amber"}`}>
          {latencyLine}
        </div>
      </div>
    </aside>
  );
}