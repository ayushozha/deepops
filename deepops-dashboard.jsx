import { useState, useEffect, useCallback, useRef } from "react";

const SPONSORS = [
  { name: "Airbyte", icon: "🔄", color: "#634BFF", role: "Ingest" },
  { name: "Aerospike", icon: "⚡", color: "#C4302B", role: "Store" },
  { name: "Macroscope", icon: "🔍", color: "#00B4D8", role: "Understand" },
  { name: "Kiro", icon: "👻", color: "#FF9900", role: "Fix" },
  { name: "Auth0", icon: "🔐", color: "#EB5424", role: "Gate" },
  { name: "Bland AI", icon: "🎙️", color: "#6366F1", role: "Escalate" },
  { name: "TrueFoundry", icon: "🚀", color: "#10B981", role: "Deploy" },
  { name: "Overmind", icon: "⚙️", color: "#A855F7", role: "Optimize" },
];

const STAGES = [
  { key: "detected", label: "DETECTED", color: "#F87171", sponsor: "Airbyte" },
  { key: "stored", label: "STORED", color: "#C4302B", sponsor: "Aerospike" },
  { key: "diagnosing", label: "DIAGNOSING", color: "#00B4D8", sponsor: "Macroscope" },
  { key: "fixing", label: "FIXING", color: "#FF9900", sponsor: "Kiro" },
  { key: "gating", label: "AUTH CHECK", color: "#EB5424", sponsor: "Auth0" },
  { key: "escalated", label: "CALLING...", color: "#6366F1", sponsor: "Bland AI" },
  { key: "deploying", label: "DEPLOYING", color: "#10B981", sponsor: "TrueFoundry" },
  { key: "resolved", label: "RESOLVED", color: "#22C55E", sponsor: "Overmind" },
];

const DEMO_ERRORS = [
  {
    id: "INC-001",
    error: "ZeroDivisionError in /calculate/0",
    file: "demo-app/main.py:14",
    severity: "medium",
    rootCause: "Missing input validation on division endpoint. Value 0 causes unhandled ZeroDivisionError.",
    fix: "Add guard clause: if value == 0: return {'error': 'Cannot divide by zero'}",
  },
  {
    id: "INC-002",
    error: "KeyError: 'name' in /user/unknown",
    file: "demo-app/main.py:21",
    severity: "high",
    rootCause: "Null reference when accessing non-existent user. users.get() returns None, then ['name'] fails.",
    fix: "Add null check: if not user: raise HTTPException(404, 'User not found')",
  },
  {
    id: "INC-003",
    error: "TimeoutError in /search endpoint",
    file: "demo-app/main.py:26",
    severity: "critical",
    rootCause: "Blocking sleep(5) in async handler causes cascading timeouts under load.",
    fix: "Replace time.sleep with await asyncio.sleep or remove artificial delay.",
  },
];

function useAnimatedNumber(target, duration = 800) {
  const [val, setVal] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    let start = val;
    let startTime = null;
    const animate = (ts) => {
      if (!startTime) startTime = ts;
      const progress = Math.min((ts - startTime) / duration, 1);
      setVal(Math.round(start + (target - start) * progress));
      if (progress < 1) ref.current = requestAnimationFrame(animate);
    };
    ref.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(ref.current);
  }, [target]);
  return val;
}

function PulsingDot({ color, size = 8 }) {
  return (
    <span style={{ position: "relative", display: "inline-block", width: size, height: size }}>
      <span
        style={{
          position: "absolute",
          width: size,
          height: size,
          borderRadius: "50%",
          background: color,
          animation: "pulse 2s ease-in-out infinite",
        }}
      />
      <span
        style={{
          position: "absolute",
          width: size,
          height: size,
          borderRadius: "50%",
          background: color,
          opacity: 0.4,
          animation: "ping 2s ease-in-out infinite",
        }}
      />
      <style>{`
        @keyframes ping { 0% { transform: scale(1); opacity: 0.4; } 100% { transform: scale(2.5); opacity: 0; } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
      `}</style>
    </span>
  );
}

function SeverityBadge({ severity }) {
  const colors = {
    low: { bg: "#064E3B", text: "#6EE7B7", border: "#065F46" },
    medium: { bg: "#78350F", text: "#FDE68A", border: "#92400E" },
    high: { bg: "#7C2D12", text: "#FDBA74", border: "#9A3412" },
    critical: { bg: "#7F1D1D", text: "#FCA5A5", border: "#991B1B" },
  };
  const c = colors[severity] || colors.medium;
  return (
    <span
      style={{
        padding: "2px 10px",
        borderRadius: 4,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: 1.2,
        textTransform: "uppercase",
        background: c.bg,
        color: c.text,
        border: `1px solid ${c.border}`,
      }}
    >
      {severity}
    </span>
  );
}

function PipelineStage({ stage, active, completed, incident }) {
  const isActive = active === stage.key;
  const isDone = completed.includes(stage.key);
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 4,
        opacity: isDone ? 0.45 : isActive ? 1 : 0.2,
        transition: "all 0.5s ease",
        transform: isActive ? "scale(1.12)" : "scale(1)",
      }}
    >
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: 8,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 18,
          background: isActive ? stage.color + "22" : isDone ? "#22C55E11" : "#1A1A2E",
          border: `2px solid ${isActive ? stage.color : isDone ? "#22C55E55" : "#2A2A3E"}`,
          position: "relative",
          boxShadow: isActive ? `0 0 20px ${stage.color}44` : "none",
        }}
      >
        {isDone ? "✓" : isActive ? <PulsingDot color={stage.color} size={10} /> : "○"}
      </div>
      <span
        style={{
          fontSize: 8,
          fontWeight: 700,
          letterSpacing: 1,
          color: isActive ? stage.color : isDone ? "#22C55E" : "#4A4A6A",
          textAlign: "center",
          maxWidth: 60,
        }}
      >
        {stage.label}
      </span>
      <span style={{ fontSize: 7, color: "#6A6A8A" }}>{stage.sponsor}</span>
    </div>
  );
}

function IncidentCard({ incident, isActive, stageIdx, onTrigger }) {
  const completedStages = STAGES.slice(0, stageIdx).map((s) => s.key);
  const activeStage = stageIdx < STAGES.length ? STAGES[stageIdx].key : "resolved";
  const resolved = stageIdx >= STAGES.length;

  return (
    <div
      style={{
        background: isActive ? "#0F0F1E" : "#0A0A16",
        border: `1px solid ${isActive ? "#3B3B5C" : "#1A1A2E"}`,
        borderRadius: 12,
        padding: 16,
        transition: "all 0.4s ease",
        boxShadow: isActive ? "0 4px 30px rgba(99,102,241,0.08)" : "none",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, fontWeight: 700, color: "#E2E8F0" }}>
            {incident.id}
          </span>
          <SeverityBadge severity={incident.severity} />
          {isActive && !resolved && <PulsingDot color={STAGES[stageIdx]?.color || "#22C55E"} />}
        </div>
        {resolved && (
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: "#22C55E",
              background: "#22C55E15",
              padding: "2px 8px",
              borderRadius: 4,
              border: "1px solid #22C55E33",
            }}
          >
            RESOLVED
          </span>
        )}
      </div>

      <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 6, fontFamily: "'JetBrains Mono', monospace" }}>
        {incident.error}
      </div>
      <div style={{ fontSize: 10, color: "#64748B", marginBottom: 12 }}>📄 {incident.file}</div>

      {stageIdx >= 3 && (
        <div style={{ background: "#0D0D1A", borderRadius: 8, padding: 10, marginBottom: 12, border: "1px solid #1E1E36" }}>
          <div style={{ fontSize: 9, color: "#00B4D8", fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>
            ROOT CAUSE
          </div>
          <div style={{ fontSize: 11, color: "#CBD5E1", lineHeight: 1.4 }}>{incident.rootCause}</div>
        </div>
      )}

      {stageIdx >= 4 && (
        <div style={{ background: "#0D0D1A", borderRadius: 8, padding: 10, marginBottom: 12, border: "1px solid #1E1E36" }}>
          <div style={{ fontSize: 9, color: "#FF9900", fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>
            PROPOSED FIX
          </div>
          <div style={{ fontSize: 11, color: "#CBD5E1", fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.5 }}>
            {incident.fix}
          </div>
        </div>
      )}

      {stageIdx >= 5 && incident.severity === "critical" && !resolved && (
        <div
          style={{
            background: "#6366F111",
            borderRadius: 8,
            padding: 10,
            marginBottom: 12,
            border: "1px solid #6366F133",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span style={{ fontSize: 18 }}>📞</span>
          <div>
            <div style={{ fontSize: 10, color: "#6366F1", fontWeight: 700, letterSpacing: 1 }}>BLAND AI VOICE CALL</div>
            <div style={{ fontSize: 11, color: "#A5B4FC" }}>Calling on-call engineer for approval...</div>
          </div>
          <PulsingDot color="#6366F1" size={8} />
        </div>
      )}

      <div style={{ display: "flex", gap: 4, alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: 3 }}>
          {STAGES.map((s, i) => (
            <PipelineStage
              key={s.key}
              stage={s}
              active={activeStage}
              completed={completedStages}
              incident={incident}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, unit, color, icon }) {
  const animVal = useAnimatedNumber(value);
  return (
    <div
      style={{
        background: "#0A0A16",
        borderRadius: 10,
        padding: "12px 16px",
        border: "1px solid #1A1A2E",
        flex: 1,
        minWidth: 130,
      }}
    >
      <div style={{ fontSize: 9, color: "#6A6A8A", fontWeight: 700, letterSpacing: 1.5, marginBottom: 6 }}>
        {icon} {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span style={{ fontSize: 28, fontWeight: 800, color, fontFamily: "'JetBrains Mono', monospace" }}>
          {animVal}
        </span>
        {unit && <span style={{ fontSize: 11, color: "#6A6A8A" }}>{unit}</span>}
      </div>
    </div>
  );
}

function SponsorStrip({ activeSponsor }) {
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
      {SPONSORS.map((s) => (
        <div
          key={s.name}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            padding: "4px 10px",
            borderRadius: 6,
            fontSize: 10,
            fontWeight: 600,
            background: activeSponsor === s.name ? s.color + "22" : "#0A0A16",
            border: `1px solid ${activeSponsor === s.name ? s.color : "#1A1A2E"}`,
            color: activeSponsor === s.name ? s.color : "#4A4A6A",
            transition: "all 0.4s ease",
            boxShadow: activeSponsor === s.name ? `0 0 12px ${s.color}33` : "none",
          }}
        >
          <span style={{ fontSize: 12 }}>{s.icon}</span>
          {s.name}
          {activeSponsor === s.name && <PulsingDot color={s.color} size={5} />}
        </div>
      ))}
    </div>
  );
}

function AgentLog({ entries }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [entries]);
  return (
    <div
      ref={ref}
      style={{
        background: "#060610",
        borderRadius: 10,
        border: "1px solid #1A1A2E",
        padding: 12,
        height: 180,
        overflowY: "auto",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      }}
    >
      {entries.map((e, i) => (
        <div key={i} style={{ marginBottom: 4, display: "flex", gap: 8, opacity: i === entries.length - 1 ? 1 : 0.6 }}>
          <span style={{ color: "#4A4A6A", minWidth: 60 }}>{e.time}</span>
          <span style={{ color: e.color || "#94A3B8" }}>{e.msg}</span>
        </div>
      ))}
      {entries.length === 0 && <div style={{ color: "#2A2A3E" }}>Waiting for incidents...</div>}
    </div>
  );
}

export default function DeepOpsDashboard() {
  const [incidents, setIncidents] = useState([]);
  const [logs, setLogs] = useState([]);
  const [metrics, setMetrics] = useState({ detected: 0, resolved: 0, avgTime: 0, llmCalls: 0 });
  const [activeSponsor, setActiveSponsor] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const intervalRef = useRef(null);
  const logRef = useRef([]);

  const addLog = useCallback((msg, color) => {
    const time = new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    logRef.current = [...logRef.current, { time, msg, color }];
    setLogs([...logRef.current]);
  }, []);

  const runSimulation = useCallback(() => {
    setIsRunning(true);
    let errorIdx = 0;
    let stageProgress = {};

    const tick = () => {
      setIncidents((prev) => {
        const updated = [...prev];

        // Maybe introduce a new error
        if (errorIdx < DEMO_ERRORS.length && Math.random() > 0.4) {
          const err = DEMO_ERRORS[errorIdx];
          updated.push({ ...err, stageIdx: 0, startTime: Date.now() });
          addLog(`🚨 ${err.id} ${err.error}`, "#F87171");
          errorIdx++;
          setMetrics((m) => ({ ...m, detected: m.detected + 1 }));
        }

        // Advance existing incidents
        updated.forEach((inc, i) => {
          if (inc.stageIdx < STAGES.length) {
            if (Math.random() > 0.3) {
              inc.stageIdx++;
              const stage = STAGES[Math.min(inc.stageIdx, STAGES.length - 1)];
              if (stage) {
                setActiveSponsor(stage.sponsor);
                const msgs = {
                  1: `⚡ ${inc.id} stored in Aerospike`,
                  2: `🔍 ${inc.id} Macroscope analyzing codebase...`,
                  3: `👻 ${inc.id} Kiro generating spec-driven fix`,
                  4: `🔐 ${inc.id} Auth0 RBAC check: severity=${inc.severity}`,
                  5: inc.severity === "critical"
                    ? `🎙️ ${inc.id} BLAND AI calling on-call engineer!`
                    : `✅ ${inc.id} Auto-approved for deployment`,
                  6: `🚀 ${inc.id} TrueFoundry deploying fix...`,
                  7: `⚙️ ${inc.id} Overmind trace logged. Agent improving.`,
                };
                if (msgs[inc.stageIdx]) addLog(msgs[inc.stageIdx], stage.color);
                setMetrics((m) => ({
                  ...m,
                  llmCalls: m.llmCalls + (inc.stageIdx === 2 || inc.stageIdx === 3 ? 2 : 1),
                  resolved: inc.stageIdx >= STAGES.length ? m.resolved + 1 : m.resolved,
                  avgTime: inc.stageIdx >= STAGES.length
                    ? Math.round(((m.avgTime * m.resolved + (Date.now() - inc.startTime)) / (m.resolved + 1)) / 1000)
                    : m.avgTime,
                }));
              }
            }
          }
        });

        return updated;
      });
    };

    intervalRef.current = setInterval(tick, 1800);
  }, [addLog]);

  const triggerBug = useCallback(() => {
    const err = DEMO_ERRORS[incidents.length % DEMO_ERRORS.length];
    const newInc = { ...err, id: `INC-${String(incidents.length + 1).padStart(3, "0")}`, stageIdx: 0, startTime: Date.now() };
    setIncidents((prev) => [...prev, newInc]);
    addLog(`🚨 ${newInc.id} ${newInc.error}`, "#F87171");
    setActiveSponsor("Airbyte");
    setMetrics((m) => ({ ...m, detected: m.detected + 1 }));
    if (!isRunning) runSimulation();
  }, [incidents, isRunning, addLog, runSimulation]);

  useEffect(() => () => clearInterval(intervalRef.current), []);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#07070F",
        color: "#E2E8F0",
        fontFamily: "'Inter', -apple-system, sans-serif",
        padding: "16px 20px",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@400;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #0A0A16; }
        ::-webkit-scrollbar-thumb { background: #2A2A3E; border-radius: 4px; }
      `}</style>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 22, fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, letterSpacing: -0.5 }}>
              <span style={{ color: "#6366F1" }}>Deep</span>
              <span style={{ color: "#22C55E" }}>Ops</span>
            </span>
            <span
              style={{
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: 2,
                color: isRunning ? "#22C55E" : "#6A6A8A",
                background: isRunning ? "#22C55E11" : "#1A1A2E",
                padding: "3px 8px",
                borderRadius: 4,
                border: `1px solid ${isRunning ? "#22C55E33" : "#2A2A3E"}`,
                display: "flex",
                alignItems: "center",
                gap: 5,
              }}
            >
              {isRunning && <PulsingDot color="#22C55E" size={5} />}
              {isRunning ? "AGENT ACTIVE" : "STANDBY"}
            </span>
          </div>
          <div style={{ fontSize: 10, color: "#4A4A6A", marginTop: 2 }}>Self-Healing Codebase Agent | Mission Control</div>
        </div>
        <button
          onClick={triggerBug}
          style={{
            background: "linear-gradient(135deg, #DC2626, #991B1B)",
            color: "#FFF",
            border: "none",
            borderRadius: 8,
            padding: "10px 20px",
            fontSize: 12,
            fontWeight: 700,
            cursor: "pointer",
            letterSpacing: 0.5,
            display: "flex",
            alignItems: "center",
            gap: 6,
            boxShadow: "0 4px 15px rgba(220,38,38,0.3)",
            transition: "transform 0.2s",
          }}
          onMouseEnter={(e) => (e.target.style.transform = "scale(1.05)")}
          onMouseLeave={(e) => (e.target.style.transform = "scale(1)")}
        >
          💥 TRIGGER BUG
        </button>
      </div>

      {/* Sponsor strip */}
      <div style={{ marginBottom: 14 }}>
        <SponsorStrip activeSponsor={activeSponsor} />
      </div>

      {/* Metrics row */}
      <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
        <MetricCard label="DETECTED" value={metrics.detected} icon="🚨" color="#F87171" />
        <MetricCard label="RESOLVED" value={metrics.resolved} icon="✅" color="#22C55E" />
        <MetricCard label="AVG RESOLVE" value={metrics.avgTime} unit="sec" icon="⏱" color="#FBBF24" />
        <MetricCard label="LLM CALLS" value={metrics.llmCalls} icon="🧠" color="#A855F7" />
      </div>

      {/* Main content: incidents + log */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div>
          <div style={{ fontSize: 10, color: "#6A6A8A", fontWeight: 700, letterSpacing: 1.5, marginBottom: 8 }}>
            ACTIVE INCIDENTS
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {incidents.length === 0 && (
              <div
                style={{
                  background: "#0A0A16",
                  borderRadius: 12,
                  padding: 30,
                  textAlign: "center",
                  border: "1px dashed #1A1A2E",
                  color: "#2A2A3E",
                  fontSize: 12,
                }}
              >
                Hit "TRIGGER BUG" to start the demo
              </div>
            )}
            {[...incidents].reverse().map((inc, i) => (
              <IncidentCard
                key={inc.id}
                incident={inc}
                isActive={inc.stageIdx < STAGES.length}
                stageIdx={inc.stageIdx}
              />
            ))}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, color: "#6A6A8A", fontWeight: 700, letterSpacing: 1.5, marginBottom: 8 }}>
            AGENT LOG
          </div>
          <AgentLog entries={logs} />

          <div style={{ fontSize: 10, color: "#6A6A8A", fontWeight: 700, letterSpacing: 1.5, marginBottom: 8, marginTop: 14 }}>
            PIPELINE ARCHITECTURE
          </div>
          <div
            style={{
              background: "#0A0A16",
              borderRadius: 10,
              border: "1px solid #1A1A2E",
              padding: 16,
            }}
          >
            {[
              { from: "Error", to: "Airbyte", desc: "Ingest error signals", color: "#634BFF" },
              { from: "Airbyte", to: "Aerospike", desc: "Store incident context", color: "#C4302B" },
              { from: "Aerospike", to: "Agent Core", desc: "Read pending incidents", color: "#6366F1" },
              { from: "Agent Core", to: "Macroscope", desc: "Understand codebase", color: "#00B4D8" },
              { from: "Agent Core", to: "Kiro", desc: "Plan + write fix (spec-driven)", color: "#FF9900" },
              { from: "Agent Core", to: "Auth0", desc: "RBAC severity gating", color: "#EB5424" },
              { from: "Auth0 (high)", to: "Bland AI", desc: "Voice-call engineer", color: "#6366F1" },
              { from: "Auth0 (low)", to: "TrueFoundry", desc: "Auto-deploy fix", color: "#10B981" },
              { from: "Everything", to: "Overmind", desc: "Trace + optimize all decisions", color: "#A855F7" },
            ].map((step, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 6,
                  fontSize: 10,
                  opacity: activeSponsor === step.to || !activeSponsor ? 1 : 0.4,
                  transition: "opacity 0.3s",
                }}
              >
                <span
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: 4,
                    background: step.color + "22",
                    border: `1px solid ${step.color}55`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 8,
                    color: step.color,
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {i + 1}
                </span>
                <span style={{ color: "#94A3B8", minWidth: 80, fontWeight: 600 }}>{step.from}</span>
                <span style={{ color: "#2A2A3E" }}>→</span>
                <span style={{ color: step.color, fontWeight: 600, minWidth: 80 }}>{step.to}</span>
                <span style={{ color: "#4A4A6A" }}>{step.desc}</span>
              </div>
            ))}
          </div>

          <div style={{ fontSize: 10, color: "#6A6A8A", fontWeight: 700, letterSpacing: 1.5, marginBottom: 8, marginTop: 14 }}>
            OVERMIND TRACES
          </div>
          <div style={{ background: "#0A0A16", borderRadius: 10, border: "1px solid #1A1A2E", padding: 12 }}>
            {incidents.length === 0 ? (
              <div style={{ color: "#2A2A3E", fontSize: 11 }}>No traces yet</div>
            ) : (
              incidents.slice(-3).map((inc) => (
                <div
                  key={inc.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "6px 0",
                    borderBottom: "1px solid #1A1A2E",
                    fontSize: 10,
                  }}
                >
                  <span style={{ color: "#A855F7", fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
                    {inc.id}
                  </span>
                  <div style={{ display: "flex", gap: 12 }}>
                    <span style={{ color: "#6A6A8A" }}>
                      LLM: <span style={{ color: "#FBBF24" }}>{Math.floor(Math.random() * 800 + 200)}ms</span>
                    </span>
                    <span style={{ color: "#6A6A8A" }}>
                      Tokens: <span style={{ color: "#A855F7" }}>{Math.floor(Math.random() * 2000 + 500)}</span>
                    </span>
                    <span style={{ color: "#6A6A8A" }}>
                      Cost: <span style={{ color: "#10B981" }}>${(Math.random() * 0.05 + 0.01).toFixed(3)}</span>
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
