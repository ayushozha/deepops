import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "../StatusBadge";
import type { IncidentStatus } from "../../types";

describe("StatusBadge", () => {
  const statuses: IncidentStatus[] = [
    "detected",
    "stored",
    "diagnosing",
    "fixing",
    "gating",
    "awaiting_approval",
    "deploying",
    "resolved",
    "blocked",
    "failed",
  ];

  it.each(statuses)("renders %s status", (status) => {
    render(<StatusBadge status={status} />);
    const displayText = status.replaceAll("_", " ");
    expect(screen.getByText(displayText)).toBeInTheDocument();
  });

  it("replaces underscores with spaces in display text", () => {
    render(<StatusBadge status="awaiting_approval" />);
    expect(screen.getByText("awaiting approval")).toBeInTheDocument();
    expect(screen.queryByText("awaiting_approval")).not.toBeInTheDocument();
  });

  it("applies resolved color classes", () => {
    render(<StatusBadge status="resolved" />);
    const el = screen.getByText("resolved");
    expect(el.className).toContain("text-emerald-100");
    expect(el.className).toContain("bg-emerald-300/10");
  });

  it("applies failed color classes", () => {
    render(<StatusBadge status="failed" />);
    const el = screen.getByText("failed");
    expect(el.className).toContain("text-red-100");
    expect(el.className).toContain("bg-red-300/10");
  });

  it("applies detected color classes", () => {
    render(<StatusBadge status="detected" />);
    const el = screen.getByText("detected");
    expect(el.className).toContain("text-slate-200");
    expect(el.className).toContain("bg-white/5");
  });

  it("applies diagnosing color classes", () => {
    render(<StatusBadge status="diagnosing" />);
    const el = screen.getByText("diagnosing");
    expect(el.className).toContain("text-cyan-100");
    expect(el.className).toContain("bg-cyan-300/10");
  });

  it("applies awaiting_approval color classes", () => {
    render(<StatusBadge status="awaiting_approval" />);
    const el = screen.getByText("awaiting approval");
    expect(el.className).toContain("text-orange-100");
    expect(el.className).toContain("bg-orange-300/10");
  });

  it("renders text in uppercase via CSS class", () => {
    render(<StatusBadge status="resolved" />);
    const el = screen.getByText("resolved");
    expect(el.className).toContain("uppercase");
  });

  it("appends custom className", () => {
    render(<StatusBadge status="resolved" className="extra" />);
    const el = screen.getByText("resolved");
    expect(el.className).toContain("extra");
  });
});
