import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { ScientificPresetDemo } from "@/components/home/ScientificPresetDemo";
import { WorkflowTour } from "@/components/home/WorkflowTour";

describe("ScientificPresetDemo", () => {
  it("labels the equation and dimensional relationship as illustrative and not run", () => {
    render(<ScientificPresetDemo />);
    expect(screen.getByText(/Illustrative example · not run/i)).toBeInTheDocument();
    expect(screen.getByText(/No validation or empirical analysis has been performed/i)).toBeInTheDocument();
    expect(screen.getByText(/not a validation result/i)).toBeInTheDocument();
    expect(screen.queryByText(/PASS|FAIL|R\^2|NIST|Solar System/i)).not.toBeInTheDocument();
  });

  it("switches illustrative equations with linked accessible tabs", () => {
    render(<ScientificPresetDemo />);
    const energyTab = screen.getByRole("tab", { name: "Rest energy" });
    fireEvent.click(energyTab);
    expect(energyTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "Rest energy" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "variables" }));
    expect(screen.getByText(/E: J · m: kg · c: m\/s/)).toBeInTheDocument();
  });

  it("supports arrow, Home, and End navigation in both tablists", () => {
    render(<ScientificPresetDemo />);
    const velocityTab = screen.getByRole("tab", { name: "Velocity" });
    const energyTab = screen.getByRole("tab", { name: "Rest energy" });
    const gravityTab = screen.getByRole("tab", { name: "Gravitational force" });

    fireEvent.keyDown(velocityTab, { key: "ArrowRight" });
    expect(energyTab).toHaveAttribute("aria-selected", "true");
    expect(energyTab).toHaveFocus();
    fireEvent.keyDown(energyTab, { key: "ArrowRight" });
    expect(gravityTab).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(gravityTab, { key: "ArrowRight" });
    expect(velocityTab).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(velocityTab, { key: "End" });
    expect(gravityTab).toHaveFocus();
    fireEvent.keyDown(gravityTab, { key: "Home" });
    expect(velocityTab).toHaveFocus();
    fireEvent.keyDown(velocityTab, { key: "ArrowLeft" });
    expect(gravityTab).toHaveAttribute("aria-selected", "true");
    expect(gravityTab).toHaveFocus();

    const dimensionsTab = screen.getByRole("tab", { name: "dimensions" });
    const variablesTab = screen.getByRole("tab", { name: "variables" });
    fireEvent.keyDown(dimensionsTab, { key: "ArrowRight" });
    expect(variablesTab).toHaveAttribute("aria-selected", "true");
    expect(variablesTab).toHaveFocus();
    fireEvent.keyDown(variablesTab, { key: "ArrowRight" });
    expect(dimensionsTab).toHaveAttribute("aria-selected", "true");
    expect(dimensionsTab).toHaveFocus();
    fireEvent.keyDown(dimensionsTab, { key: "ArrowLeft" });
    expect(variablesTab).toHaveFocus();
    fireEvent.keyDown(variablesTab, { key: "Home" });
    expect(dimensionsTab).toHaveFocus();
    fireEvent.keyDown(dimensionsTab, { key: "End" });
    expect(variablesTab).toHaveFocus();
  });

  it("switches detail tabs and exposes their associated panels", () => {
    render(<ScientificPresetDemo />);
    const variablesTab = screen.getByRole("tab", { name: "variables" });
    fireEvent.click(variablesTab);
    expect(variablesTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/v: m\/s/)).toBeInTheDocument();
  });

  it("presents workflow telemetry and bundle details as unrun illustrations", () => {
    render(<WorkflowTour />);
    fireEvent.click(screen.getByRole("tab", { name: /Run and Review Validation/i }));
    expect(screen.getByText(/Illustrative interface only · no run or export performed/i)).toBeInTheDocument();
    expect(screen.getByTestId("mockup-verification")).toHaveTextContent(/Not run/);
    expect(screen.getByTestId("mockup-verification")).toHaveTextContent(/Layer 6: Definition unresolved/i);
    expect(screen.queryByText(/PASS|\d+\.\d+ms/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /Export a Research Bundle/i }));
    expect(screen.getByTestId("mockup-bundle")).toHaveTextContent(/no export or cryptographic verification performed/i);
    expect(screen.getByTestId("mockup-bundle")).toHaveTextContent(/No digest generated/i);
  });

  it("supports arrow, Home, and End keyboard navigation for workflow steps", () => {
    render(<WorkflowTour />);
    const declareTab = screen.getByRole("tab", { name: /Declare Physical Quantities/i });
    const composeTab = screen.getByRole("tab", { name: /Compose Equation Nodes/i });
    const validationTab = screen.getByRole("tab", { name: /Run and Review Validation/i });
    const exportTab = screen.getByRole("tab", { name: /Export a Research Bundle/i });

    fireEvent.keyDown(declareTab, { key: "ArrowRight" });
    expect(composeTab).toHaveAttribute("aria-selected", "true");
    expect(composeTab).toHaveFocus();
    fireEvent.keyDown(composeTab, { key: "ArrowLeft" });
    expect(declareTab).toHaveFocus();
    fireEvent.keyDown(declareTab, { key: "ArrowLeft" });
    expect(exportTab).toHaveAttribute("aria-selected", "true");
    expect(exportTab).toHaveFocus();
    fireEvent.keyDown(exportTab, { key: "Home" });
    expect(declareTab).toHaveFocus();
    fireEvent.keyDown(declareTab, { key: "End" });
    expect(exportTab).toHaveFocus();
    fireEvent.keyDown(exportTab, { key: "ArrowLeft" });
    expect(validationTab).toHaveFocus();
  });
});
