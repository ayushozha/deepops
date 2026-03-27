import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DiffViewer } from "../DiffViewer";
import { mockIncidentPending } from "../../__tests__/fixtures";
import type { Incident } from "../../types";

describe("DiffViewer", () => {
  it("shows placeholder when incident is null", () => {
    render(<DiffViewer incident={null} />);
    expect(
      screen.getByText("Select an incident to inspect the generated patch."),
    ).toBeInTheDocument();
  });

  it("renders diff lines with correct coloring for additions", () => {
    render(<DiffViewer incident={mockIncidentPending} />);
    // whitespace-pre means getByText normalisation may differ; use a function matcher
    const addLine = screen.getByText((_content, element) =>
      element?.textContent === "+  if (!payment) {" && element.tagName === "DIV",
    );
    expect(addLine.className).toContain("bg-emerald-400/10");
    expect(addLine.className).toContain("text-emerald-100");
  });

  it("renders diff lines with correct coloring for removals", () => {
    const incident: Incident = {
      ...mockIncidentPending,
      fix: {
        ...mockIncidentPending.fix,
        diff_preview:
          "--- a/file.ts\n+++ b/file.ts\n-  old line\n+  new line\n   context line",
      },
    };
    render(<DiffViewer incident={incident} />);
    const removeLine = screen.getByText((_content, element) =>
      element?.textContent === "-  old line" && element.tagName === "DIV",
    );
    expect(removeLine.className).toContain("bg-red-400/10");
    expect(removeLine.className).toContain("text-red-100");
  });

  it("renders context lines with gray text", () => {
    render(<DiffViewer incident={mockIncidentPending} />);
    const contextLine = screen.getByText("const payment = await getPayment(id);", { exact: false });
    expect(contextLine.className).toContain("text-slate-300");
  });

  it("renders file list when incident has files_changed", () => {
    render(<DiffViewer incident={mockIncidentPending} />);
    expect(screen.getByText("src/handlers/payment.ts")).toBeInTheDocument();
  });

  it("renders spec accordion when incident has spec_markdown", () => {
    render(<DiffViewer incident={mockIncidentPending} />);
    const summary = screen.getByText("Open spec_markdown");
    expect(summary).toBeInTheDocument();
    // The spec content is rendered in a whitespace-pre-wrap div inside <details>
    const specContent = screen.getByText((_content, element) =>
      element?.tagName === "DIV" &&
      element.classList.contains("whitespace-pre-wrap") &&
      (element.textContent?.includes("Fix Spec") ?? false),
    );
    expect(specContent).toBeInTheDocument();
  });

  it("shows 'No diff preview' message when incident has no diff", () => {
    const incident: Incident = {
      ...mockIncidentPending,
      fix: {
        ...mockIncidentPending.fix,
        diff_preview: null,
      },
    };
    render(<DiffViewer incident={incident} />);
    expect(
      screen.getByText(
        "No diff preview is available for the selected incident.",
      ),
    ).toBeInTheDocument();
  });

  it("shows root_cause and confidence", () => {
    render(<DiffViewer incident={mockIncidentPending} />);
    expect(
      screen.getByText("Missing null check in payment handler"),
    ).toBeInTheDocument();
    expect(screen.getByText("92%")).toBeInTheDocument();
  });

  it("shows suggested_fix", () => {
    render(<DiffViewer incident={mockIncidentPending} />);
    expect(
      screen.getByText("Add null guard before accessing payment.id"),
    ).toBeInTheDocument();
  });

  it("shows test_plan items", () => {
    render(<DiffViewer incident={mockIncidentPending} />);
    expect(screen.getByText("Test with valid payment ID")).toBeInTheDocument();
    expect(
      screen.getByText("Test with non-existent payment ID"),
    ).toBeInTheDocument();
  });

  it("shows 'Pending diagnosis' when root_cause is null", () => {
    const incident: Incident = {
      ...mockIncidentPending,
      diagnosis: {
        ...mockIncidentPending.diagnosis,
        root_cause: null,
      },
    };
    render(<DiffViewer incident={incident} />);
    expect(screen.getByText("Pending diagnosis")).toBeInTheDocument();
  });

  it("shows 'Pending' confidence when confidence is null", () => {
    const incident: Incident = {
      ...mockIncidentPending,
      diagnosis: {
        ...mockIncidentPending.diagnosis,
        confidence: null,
      },
    };
    render(<DiffViewer incident={incident} />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });
});
