"use client";

import { useState } from "react";

import { submitApprovalDecision } from "../api";
import type { ApprovalDecisionBody, ApprovalDecisionResponse } from "../types";

type SubmitApprovalOptions = ApprovalDecisionBody;

export function useApproval() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitDecision = async (
    incidentId: string,
    options: SubmitApprovalOptions,
  ): Promise<ApprovalDecisionResponse> => {
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await submitApprovalDecision(incidentId, options);
      setError(null);
      return response;
    } catch (caughtError) {
      const message =
        caughtError instanceof Error
          ? caughtError.message
          : "Failed to submit approval decision.";
      setError(message);
      throw caughtError;
    } finally {
      setIsSubmitting(false);
    }
  };

  const approve = (
    incidentId: string,
    options: Omit<SubmitApprovalOptions, "approved" | "decision"> = {},
  ) => submitDecision(incidentId, { ...options, approved: true });

  const reject = (
    incidentId: string,
    options: Omit<SubmitApprovalOptions, "approved" | "decision"> = {},
  ) => submitDecision(incidentId, { ...options, approved: false });

  return {
    approve,
    reject,
    submitDecision,
    isSubmitting,
    error,
    clearError() {
      setError(null);
    },
  };
}
