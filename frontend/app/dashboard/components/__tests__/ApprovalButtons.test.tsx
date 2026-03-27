import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApprovalButtons } from "../ApprovalButtons";
import {
  mockIncidentPending,
  mockIncidentResolved,
} from "../../__tests__/fixtures";
import type { Incident } from "../../types";

const noop = () => {};

describe("ApprovalButtons", () => {
  it("shows 'Choose an incident' message when incident is null", () => {
    render(
      <ApprovalButtons
        incident={null}
        onApprove={noop}
        onReject={noop}
      />,
    );
    expect(
      screen.getByText("Choose an incident to see the approval gate."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /reject/i })).not.toBeInTheDocument();
  });

  it("shows 'No action required' when status is not awaiting_approval", () => {
    const incident: Incident = {
      ...mockIncidentPending,
      status: "diagnosing",
    };
    render(
      <ApprovalButtons
        incident={incident}
        onApprove={noop}
        onReject={noop}
      />,
    );
    expect(screen.getByText("No action required")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /reject/i })).not.toBeInTheDocument();
  });

  it("shows approval status pill and no buttons when approval.status is not pending", () => {
    render(
      <ApprovalButtons
        incident={mockIncidentResolved}
        onApprove={noop}
        onReject={noop}
      />,
    );
    expect(screen.getByText("approved")).toBeInTheDocument();
    expect(screen.getByText("No action required")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
  });

  it("shows APPROVE and REJECT buttons when awaiting_approval and pending", () => {
    render(
      <ApprovalButtons
        incident={mockIncidentPending}
        onApprove={noop}
        onReject={noop}
      />,
    );
    expect(screen.getByRole("button", { name: "APPROVE" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "REJECT" })).toBeInTheDocument();
  });

  it("calls onApprove when APPROVE button is clicked", () => {
    const onApprove = vi.fn();
    render(
      <ApprovalButtons
        incident={mockIncidentPending}
        onApprove={onApprove}
        onReject={noop}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "APPROVE" }));
    expect(onApprove).toHaveBeenCalledOnce();
  });

  it("calls onReject when REJECT button is clicked", () => {
    const onReject = vi.fn();
    render(
      <ApprovalButtons
        incident={mockIncidentPending}
        onApprove={noop}
        onReject={onReject}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "REJECT" }));
    expect(onReject).toHaveBeenCalledOnce();
  });

  it("shows SUBMITTING and disables buttons when isSubmitting is true", () => {
    render(
      <ApprovalButtons
        incident={mockIncidentPending}
        isSubmitting={true}
        onApprove={noop}
        onReject={noop}
      />,
    );
    const buttons = screen.getAllByRole("button", { name: "SUBMITTING" });
    expect(buttons).toHaveLength(2);
    buttons.forEach((btn) => {
      expect(btn).toBeDisabled();
    });
  });

  it("shows error message when error prop is provided", () => {
    render(
      <ApprovalButtons
        incident={mockIncidentPending}
        error="Something went wrong"
        onApprove={noop}
        onReject={noop}
      />,
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("shows approval status pill when incident is present", () => {
    render(
      <ApprovalButtons
        incident={mockIncidentPending}
        onApprove={noop}
        onReject={noop}
      />,
    );
    expect(screen.getByText("pending")).toBeInTheDocument();
  });
});
