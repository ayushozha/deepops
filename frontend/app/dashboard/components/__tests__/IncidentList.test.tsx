import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { IncidentList } from "../IncidentList";
import {
  mockIncidentPending,
  mockIncidentResolved,
} from "../../__tests__/fixtures";
const noop = () => {};

describe("IncidentList", () => {
  it("renders empty state when incidents array is empty", () => {
    render(
      <IncidentList
        incidents={[]}
        selectedIncidentId={null}
        onSelect={noop}
      />,
    );
    expect(screen.getByText("No incidents detected")).toBeInTheDocument();
  });

  it("renders incident cards with severity badge", () => {
    render(
      <IncidentList
        incidents={[mockIncidentPending]}
        selectedIncidentId={null}
        onSelect={noop}
      />,
    );
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("renders short ID for incident", () => {
    render(
      <IncidentList
        incidents={[mockIncidentPending]}
        selectedIncidentId={null}
        onSelect={noop}
      />,
    );
    // shortId: "inc-" (first 4) + "..." + "7890" (last 4)
    expect(screen.getByText("inc-…7890")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    render(
      <IncidentList
        incidents={[mockIncidentPending]}
        selectedIncidentId={null}
        onSelect={noop}
      />,
    );
    expect(screen.getByText("awaiting approval")).toBeInTheDocument();
  });

  it("renders service / environment", () => {
    render(
      <IncidentList
        incidents={[mockIncidentPending]}
        selectedIncidentId={null}
        onSelect={noop}
      />,
    );
    expect(screen.getByText("payment-api / production")).toBeInTheDocument();
  });

  it("renders error info", () => {
    render(
      <IncidentList
        incidents={[mockIncidentPending]}
        selectedIncidentId={null}
        onSelect={noop}
      />,
    );
    expect(
      screen.getByText(
        "NullPointerException: Cannot read property 'id' of null",
      ),
    ).toBeInTheDocument();
  });

  it("highlights selected incident", () => {
    render(
      <IncidentList
        incidents={[mockIncidentPending]}
        selectedIncidentId={mockIncidentPending.incident_id}
        onSelect={noop}
      />,
    );
    const button = screen.getByRole("button");
    expect(button.className).toContain("border-cyan-300/55");
    expect(button.className).toContain("bg-cyan-300/10");
  });

  it("does not highlight non-selected incident", () => {
    render(
      <IncidentList
        incidents={[mockIncidentPending]}
        selectedIncidentId="other-id"
        onSelect={noop}
      />,
    );
    const button = screen.getByRole("button");
    expect(button.className).not.toContain("border-cyan-300/55");
  });

  it("calls onSelect when incident is clicked", () => {
    const onSelect = vi.fn();
    render(
      <IncidentList
        incidents={[mockIncidentPending]}
        selectedIncidentId={null}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledWith(mockIncidentPending.incident_id);
  });

  it("renders multiple incidents", () => {
    render(
      <IncidentList
        incidents={[mockIncidentPending, mockIncidentResolved]}
        selectedIncidentId={null}
        onSelect={noop}
      />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(2);
  });
});
