import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SeverityBadge } from "../SeverityBadge";
import type { IncidentSeverity } from "../../types";

describe("SeverityBadge", () => {
  const severities: IncidentSeverity[] = [
    "critical",
    "high",
    "medium",
    "low",
    "pending",
  ];

  it.each(severities)("renders %s severity level", (severity) => {
    render(<SeverityBadge severity={severity} />);
    expect(screen.getByText(severity)).toBeInTheDocument();
  });

  it("renders severity text in uppercase via CSS class", () => {
    render(<SeverityBadge severity="high" />);
    const el = screen.getByText("high");
    expect(el.className).toContain("uppercase");
  });

  it("applies critical color classes", () => {
    render(<SeverityBadge severity="critical" />);
    const el = screen.getByText("critical");
    expect(el.className).toContain("text-[#ffd6d6]");
    expect(el.className).toContain("bg-[#ff4444]/12");
  });

  it("applies high color classes", () => {
    render(<SeverityBadge severity="high" />);
    const el = screen.getByText("high");
    expect(el.className).toContain("text-[#ffe0c2]");
    expect(el.className).toContain("bg-[#ff8800]/12");
  });

  it("applies medium color classes", () => {
    render(<SeverityBadge severity="medium" />);
    const el = screen.getByText("medium");
    expect(el.className).toContain("text-[#fff0b8]");
    expect(el.className).toContain("bg-[#ffcc00]/12");
  });

  it("applies low color classes", () => {
    render(<SeverityBadge severity="low" />);
    const el = screen.getByText("low");
    expect(el.className).toContain("text-[#c8ffe4]");
    expect(el.className).toContain("bg-[#00ff88]/12");
  });

  it("applies pending color classes", () => {
    render(<SeverityBadge severity="pending" />);
    const el = screen.getByText("pending");
    expect(el.className).toContain("text-slate-200");
    expect(el.className).toContain("bg-white/5");
  });

  it("appends custom className", () => {
    render(<SeverityBadge severity="low" className="my-custom" />);
    const el = screen.getByText("low");
    expect(el.className).toContain("my-custom");
  });
});
