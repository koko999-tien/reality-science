import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { VariableDeclarationPanel } from "@/components/equations/VariableDeclarationPanel";
import { VariableSpec } from "@/types/contracts";

describe("VariableDeclarationPanel Component", () => {
  const initialVars: VariableSpec[] = [
    { symbol: "v", name: "Velocity", unit: "meter / second", domain: "real" },
    { symbol: "m", name: "Mass", unit: "kilogram", domain: "positive_real" },
  ];

  it("renders the table with declared variables and count badge", () => {
    const onVariablesChange = jest.fn();
    render(
      <VariableDeclarationPanel
        variables={initialVars}
        onVariablesChange={onVariablesChange}
        usedSymbols={new Set(["v"])}
      />
    );

    expect(screen.getByText("Symbol-First Declaration Panel")).toBeInTheDocument();
    expect(screen.getByText("2 declared")).toBeInTheDocument();
    expect(screen.getByText("Velocity")).toBeInTheDocument();
    expect(screen.getByText("Mass")).toBeInTheDocument();
    expect(screen.getByText("In Use")).toBeInTheDocument();
    expect(screen.getByText("Unused")).toBeInTheDocument();
  });

  it("rejects invalid variable symbol format", () => {
    const onVariablesChange = jest.fn();
    render(
      <VariableDeclarationPanel
        variables={initialVars}
        onVariablesChange={onVariablesChange}
      />
    );

    const symbolInput = screen.getByLabelText("Variable symbol");
    const nameInput = screen.getByLabelText("Variable name");
    const declareButton = screen.getByRole("button", { name: /Declare Symbol/i });

    // Invalid symbol: starts with digit or has dash
    fireEvent.change(symbolInput, { target: { value: "123invalid" } });
    fireEvent.change(nameInput, { target: { value: "Invalid Variable" } });
    fireEvent.click(declareButton);

    expect(onVariablesChange).not.toHaveBeenCalled();
    expect(screen.getByText(/Invalid symbol format/i)).toBeInTheDocument();
  });

  it("rejects duplicate variable symbol", () => {
    const onVariablesChange = jest.fn();
    render(
      <VariableDeclarationPanel
        variables={initialVars}
        onVariablesChange={onVariablesChange}
      />
    );

    const symbolInput = screen.getByLabelText("Variable symbol");
    const nameInput = screen.getByLabelText("Variable name");
    const declareButton = screen.getByRole("button", { name: /Declare Symbol/i });

    // Duplicate symbol 'v'
    fireEvent.change(symbolInput, { target: { value: "v" } });
    fireEvent.change(nameInput, { target: { value: "Another Velocity" } });
    fireEvent.click(declareButton);

    expect(onVariablesChange).not.toHaveBeenCalled();
    expect(screen.getByText(/already declared/i)).toBeInTheDocument();
  });

  it("adds a valid variable successfully", () => {
    const onVariablesChange = jest.fn();
    render(
      <VariableDeclarationPanel
        variables={initialVars}
        onVariablesChange={onVariablesChange}
      />
    );

    const symbolInput = screen.getByLabelText("Variable symbol");
    const nameInput = screen.getByLabelText("Variable name");
    const declareButton = screen.getByRole("button", { name: /Declare Symbol/i });

    fireEvent.change(symbolInput, { target: { value: "E" } });
    fireEvent.change(nameInput, { target: { value: "Energy" } });
    fireEvent.click(declareButton);

    expect(onVariablesChange).toHaveBeenCalledWith([
      ...initialVars,
      {
        symbol: "E",
        name: "Energy",
        unit: "meter",
        domain: "real",
        latex_presentation: "E",
      },
    ]);
  });

  it("deletes a variable when trash icon is clicked", () => {
    const onVariablesChange = jest.fn();
    render(
      <VariableDeclarationPanel
        variables={initialVars}
        onVariablesChange={onVariablesChange}
      />
    );

    const deleteBtn = screen.getByLabelText("Delete variable m");
    fireEvent.click(deleteBtn);

    expect(onVariablesChange).toHaveBeenCalledWith([initialVars[0]]);
  });
});
