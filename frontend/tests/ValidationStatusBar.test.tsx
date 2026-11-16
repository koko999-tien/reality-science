import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { ValidationStatusBar } from "@/components/equations/ValidationStatusBar";
import { FindingResult, FindingState } from "@/types/contracts";

describe("ValidationStatusBar Component", () => {
  it("renders NOT YET TESTED by default when result is null", () => {
    render(<ValidationStatusBar result={null} />);
    const badge = screen.getByTestId("finding-state-badge");
    expect(badge).toHaveTextContent("NOT YET TESTED");
    expect(screen.getByText("UNVERIFIED")).toBeInTheDocument();
  });

  it("renders PASS state with verified dimensions and simplification", () => {
    const result: FindingResult = {
      job_id: "job-12345678",
      state: "PASS",
      diagnostic_code: "DIM_HOMOGENEOUS",
      message: "Formula passed all reality constraint checks.",
      symbolic_simplification: "a \\cdot t",
      dimensions_verified: true,
      diagnostics: ["Layer 1: OK", "Layer 2: OK"],
    };

    render(<ValidationStatusBar result={result} />);
    const badge = screen.getByTestId("finding-state-badge");
    expect(badge).toHaveTextContent("PASS");
    expect(screen.getByText("Backend validation response")).toBeInTheDocument();
    expect(screen.getByText("The validation API returned PASS. Only checks represented in this response are reported here.")).toBeInTheDocument();
    expect(screen.getByText("API REPORTED VERIFIED")).toBeInTheDocument();
    expect(screen.getByText("DIM_HOMOGENEOUS")).toBeInTheDocument();
    expect(screen.getByText("Layer 1: OK")).toBeInTheDocument();
    expect(screen.getByText("Job: job-1234")).toBeInTheDocument();
  });

  it("does not present a local preflight PASS as a backend finding", () => {
    const result: FindingResult = {
      job_id: "local-1700000000000",
      state: "PASS",
      diagnostic_code: "PREFLIGHT_OK",
      message: "Client preflight passed.",
      dimensions_verified: true,
      diagnostics: ["Local syntax check passed."],
      layer_findings: {
        1: {
          layer: 1,
          name: "Syntax",
          state: "PASS",
          diagnostic_code: "LOCAL_OK",
          message: "Local syntax check passed.",
          diagnostics: [],
        },
      },
    };

    render(<ValidationStatusBar result={result} />);

    expect(screen.getByTestId("finding-state-badge")).toHaveTextContent("PREFLIGHT");
    expect(screen.getByText("Local preflight · limited checks")).toBeInTheDocument();
    expect(screen.getByText("Client-side checks only. This is not a backend validation finding or a full RCE verdict.")).toBeInTheDocument();
    expect(screen.getByText("UNVERIFIED")).toBeInTheDocument();
    expect(screen.getByText("Limited local checks only; no backend validation result is available.")).toBeInTheDocument();
    expect(screen.queryByText("Backend validation response")).not.toBeInTheDocument();
    expect(screen.queryByText("PREFLIGHT_OK")).not.toBeInTheDocument();
    expect(screen.queryByText("Job: local-170")).not.toBeInTheDocument();
    expect(screen.queryByText("Local syntax check passed.")).not.toBeInTheDocument();
    expect(screen.queryByText("API REPORTED VERIFIED")).not.toBeInTheDocument();
  });

  it("renders FAIL state with diagnostics", () => {
    const result: FindingResult = {
      job_id: "job-87654321",
      state: "FAIL",
      diagnostic_code: "DIMENSIONAL_MISMATCH",
      message: "Cannot add [length] and [time].",
      dimensions_verified: false,
      diagnostics: ["Incompatible unit addition: meter + second"],
    };

    render(<ValidationStatusBar result={result} />);
    const badge = screen.getByTestId("finding-state-badge");
    expect(badge).toHaveTextContent("FAIL");
    expect(screen.getByText("DIMENSIONAL_MISMATCH")).toBeInTheDocument();
    expect(screen.getByText("Cannot add [length] and [time].")).toBeInTheDocument();
  });

  it.each<FindingState>([
    "WARNING",
    "NOT_APPLICABLE",
    "INSUFFICIENT_DATA",
    "NEEDS_EXPERT_REVIEW",
  ])("correctly displays badge for canonical state '%s'", (state) => {
    const result: FindingResult = {
      job_id: "job-test",
      state,
      diagnostic_code: `CODE_${state}`,
      message: `State message for ${state}`,
      dimensions_verified: false,
      diagnostics: [],
    };

    render(<ValidationStatusBar result={result} />);
    const badge = screen.getByTestId("finding-state-badge");
    expect(badge).toHaveTextContent(state.replace(/_/g, " "));
  });

  it("triggers onValidate when button is clicked", () => {
    const onValidate = jest.fn();
    render(<ValidationStatusBar result={null} onValidate={onValidate} />);

    const button = screen.getByRole("button", { name: /Run Compute Verification/i });
    fireEvent.click(button);
    expect(onValidate).toHaveBeenCalledTimes(1);
  });

  it("displays loading state during verification", () => {
    render(<ValidationStatusBar result={{
      job_id: "job-stale",
      state: "PASS",
      diagnostic_code: "DIM_HOMOGENEOUS",
      message: "Previous result",
      dimensions_verified: true,
      diagnostics: ["Previous layer finding"],
    }} isValidating={true} />);
    const badge = screen.getByTestId("finding-state-badge");
    expect(badge).toHaveTextContent("COMPUTING...");
    expect(badge).not.toHaveTextContent("PASS");
    expect(screen.getByText("Compute request in progress")).toBeInTheDocument();
    expect(screen.getByText("Previous results are hidden until this request completes.")).toBeInTheDocument();
    expect(screen.queryByText("API REPORTED VERIFIED")).not.toBeInTheDocument();
    expect(screen.queryByText("Previous result")).not.toBeInTheDocument();
    expect(screen.queryByText("Previous layer finding")).not.toBeInTheDocument();
  });
});
