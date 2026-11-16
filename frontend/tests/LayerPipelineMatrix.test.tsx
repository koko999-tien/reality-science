import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { LayerPipelineMatrix } from "@/components/equations/LayerPipelineMatrix";
import { LayerFinding } from "@/types/contracts";

describe("LayerPipelineMatrix Component", () => {
  it("renders all 6 layers with pending status when empty", () => {
    render(<LayerPipelineMatrix layers={{}} />);
    expect(screen.getByTestId("layer-pipeline-matrix")).toBeInTheDocument();
    expect(screen.getByText("Layer 1: Syntax & Semantics")).toBeInTheDocument();
    expect(screen.getByText("Layer 2: Boundary & Singularities")).toBeInTheDocument();
    expect(screen.getByText("Layer 3: Dimensional Analysis")).toBeInTheDocument();
    expect(screen.getByText("Layer 4: Physical Laws & Invariants")).toBeInTheDocument();
    expect(screen.getByText("Layer 5: Empirical Correlation")).toBeInTheDocument();
    expect(screen.getByText("Layer 6: Definition Pending")).toBeInTheDocument();
    const pendingBadges = screen.getAllByText("PENDING");
    expect(pendingBadges.length).toBe(6);
  });

  it("renders specific layer findings with correct state pills and expands details", () => {
    const layers: Record<number, LayerFinding> = {
      1: {
        layer: 1,
        name: "Layer 1: Syntax & Semantics",
        state: "PASS",
        diagnostic_code: "VALIDATION_PASSED",
        message: "AST syntax valid across 3 declared symbols.",
        diagnostics: ["Referenced symbols: [v, t]"],
      },
      2: {
        layer: 2,
        name: "Layer 2: Boundary & Singularities",
        state: "PASS",
        diagnostic_code: "VALIDATION_PASSED",
        message: "Boundary analysis passed.",
        diagnostics: ["Simplified: v*t"],
      },
      3: {
        layer: 3,
        name: "Layer 3: Dimensional Analysis",
        state: "PASS",
        diagnostic_code: "VALIDATION_PASSED",
        message: "Dimensional consistency verified: [length]",
        diagnostics: ["Inferred dimension: meter"],
      },
      4: {
        layer: 4,
        name: "Layer 4: Physical Laws & Invariants",
        state: "NOT_APPLICABLE",
        diagnostic_code: "NO_SYSTEM_CONTEXT",
        message: "No physical system context declared for invariant checks.",
        diagnostics: [],
      },
      5: {
        layer: 5,
        name: "Layer 5: Empirical Correlation",
        state: "FAIL",
        diagnostic_code: "EMPIRICAL_FIT_FAILED",
        message: "Residual chi-squared exceeded 3-sigma tolerance.",
        diagnostics: ["Chi2/ndf = 4.82"],
        details: { chi2: 4.82, p_value: 0.001 },
      },
      6: {
        layer: 6,
        name: "Layer 6: Backend-provided finding",
        state: "WARNING",
        diagnostic_code: "BACKEND_WARNING",
        message: "A backend warning was returned for this layer.",
        diagnostics: ["Review the backend response for details."],
      },
    };

    render(<LayerPipelineMatrix layers={layers} />);

    expect(screen.getAllByText("PASS").length).toBe(3);
    expect(screen.getByText("N/A")).toBeInTheDocument();
    expect(screen.getByText("FAIL")).toBeInTheDocument();
    expect(screen.getByText("WARNING")).toBeInTheDocument();

    // Click on Layer 5 to expand details
    const l5Message = screen.getByText("Residual chi-squared exceeded 3-sigma tolerance.");
    fireEvent.click(l5Message);

    // Diagnostics and code should now be visible
    expect(screen.getByText("EMPIRICAL_FIT_FAILED")).toBeInTheDocument();
    expect(screen.getByText("Chi2/ndf = 4.82")).toBeInTheDocument();
    expect(screen.getByText("Evaluation Payload:")).toBeInTheDocument();
  });
});
