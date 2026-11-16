import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConstantNode } from "@/components/equations/canvas/nodes/ConstantNode";
import { VariableNode } from "@/components/equations/canvas/nodes/VariableNode";
import { BinaryOpNode } from "@/components/equations/canvas/nodes/BinaryOpNode";
import { UnaryOpNode } from "@/components/equations/canvas/nodes/UnaryOpNode";
import { FunctionCallNode } from "@/components/equations/canvas/nodes/FunctionCallNode";
import { EquationRootNode } from "@/components/equations/canvas/nodes/EquationRootNode";

// Mock ReactFlow handles since they rely on ReactFlow context in browser
jest.mock("@xyflow/react", () => {
  const actual = jest.requireActual("@xyflow/react");
  return {
    ...actual,
    Handle: ({ id, position }: { id?: string; position?: string }) => (
      <div data-testid={`handle-${id || "default"}`} data-position={position} />
    ),
  };
});

describe("Custom Canvas Nodes", () => {
  describe("ConstantNode", () => {
    it("renders value and triggers onChange on user input", () => {
      const onChange = jest.fn();
      render(
        <ConstantNode
          id="c1"
          data={{ value: 42, onChange }}
          type="constantNode"
          zIndex={1}
          isConnectable={true}
          positionAbsoluteX={0}
          positionAbsoluteY={0}
          selected={false}
          dragging={false}
          selectable={true}
          deletable={true}
          draggable={true}
        />
      );

      const input = screen.getByLabelText("Constant value for node c1");
      expect(input).toHaveValue(42);

      fireEvent.change(input, { target: { value: "100" } });
      expect(onChange).toHaveBeenCalledWith(100);
    });
  });

  describe("VariableNode", () => {
    it("renders available variable options and triggers onChange", () => {
      const onChange = jest.fn();
      const availableSymbols = [
        { symbol: "v", name: "Velocity", unit: "meter / second" },
        { symbol: "t", name: "Time", unit: "second" },
      ];

      render(
        <VariableNode
          id="v1"
          data={{ symbol: "v", availableSymbols, onChange }}
          type="variableNode"
          zIndex={1}
          isConnectable={true}
          positionAbsoluteX={0}
          positionAbsoluteY={0}
          selected={false}
          dragging={false}
          selectable={true}
          deletable={true}
          draggable={true}
        />
      );

      const select = screen.getByLabelText("Variable symbol for node v1");
      expect(select).toHaveValue("v");
      expect(screen.getByText("[meter / second]")).toBeInTheDocument();

      fireEvent.change(select, { target: { value: "t" } });
      expect(onChange).toHaveBeenCalledWith("t");
    });

    it.each(["another declaration remains", "no declarations remain"])("keeps a removed symbol visible when %s", (scenario) => {
      const onChange = jest.fn();
      const x = { symbol: "x", name: "Length", unit: "meter" };
      const y = { symbol: "y", name: "Time", unit: "second" };
      const props = {
        id: "v1", type: "variableNode" as const, zIndex: 1, isConnectable: true,
        positionAbsoluteX: 0, positionAbsoluteY: 0, selected: false, dragging: false,
        selectable: true, deletable: true, draggable: true,
      };
      const data = { symbol: "x", unit: "meter", onChange };
      const { rerender } = render(<VariableNode {...props} data={{ ...data, availableSymbols: [x, y] }} />);
      expect(screen.getByLabelText("Variable symbol for node v1")).toHaveValue("x");
      expect(screen.getByText("[meter]")).toBeInTheDocument();

      const remaining = scenario === "another declaration remains" ? [y] : [];
      rerender(<VariableNode {...props} data={{ ...data, availableSymbols: remaining }} />);
      const control = screen.getByLabelText("Variable symbol for node v1");
      expect(control).toHaveValue("x");
      expect(control).toHaveAttribute("aria-invalid", "true");
      expect(screen.queryByText("[meter]")).not.toBeInTheDocument();
      expect(onChange).not.toHaveBeenCalled();
      if (remaining.length) {
        expect(screen.getByRole("option", { name: "x (undeclared)" })).toBeDisabled();
        fireEvent.change(control, { target: { value: "y" } });
        expect(onChange).toHaveBeenCalledWith("y");
      }

      rerender(<VariableNode {...props} data={{ ...data, availableSymbols: [{ ...x, unit: "second" }, y] }} />);
      expect(screen.getByLabelText("Variable symbol for node v1")).toHaveValue("x");
      expect(screen.getByLabelText("Variable symbol for node v1")).not.toHaveAttribute("aria-invalid");
      expect(screen.queryByRole("option", { name: "x (undeclared)" })).not.toBeInTheDocument();
      expect(screen.getByText("[second]")).toBeInTheDocument();
    });
  });

  describe("BinaryOpNode", () => {
    it("renders operator selector and triggers onChange", () => {
      const onChange = jest.fn();
      render(
        <BinaryOpNode
          id="b1"
          data={{ op: "+", onChange }}
          type="binaryOpNode"
          zIndex={1}
          isConnectable={true}
          positionAbsoluteX={0}
          positionAbsoluteY={0}
          selected={false}
          dragging={false}
          selectable={true}
          deletable={true}
          draggable={true}
        />
      );

      const select = screen.getByLabelText("Binary operator for node b1");
      expect(select).toHaveValue("+");

      fireEvent.change(select, { target: { value: "*" } });
      expect(onChange).toHaveBeenCalledWith("*");
    });
  });

  describe("UnaryOpNode", () => {
    it("renders negate label and handles", () => {
      render(
        <UnaryOpNode
          id="u1"
          data={{ op: "neg" }}
          type="unaryOpNode"
          zIndex={1}
          isConnectable={true}
          positionAbsoluteX={0}
          positionAbsoluteY={0}
          selected={false}
          dragging={false}
          selectable={true}
          deletable={true}
          draggable={true}
        />
      );

      expect(screen.getByText("Negate (−)")).toBeInTheDocument();
      expect(screen.getByTestId("handle-left")).toBeInTheDocument();
      expect(screen.getByTestId("handle-output")).toBeInTheDocument();
    });
  });

  describe("FunctionCallNode", () => {
    it("renders function selector and triggers onChange", () => {
      const onChange = jest.fn();
      render(
        <FunctionCallNode
          id="f1"
          data={{ func: "sqrt", onChange }}
          type="functionCallNode"
          zIndex={1}
          isConnectable={true}
          positionAbsoluteX={0}
          positionAbsoluteY={0}
          selected={false}
          dragging={false}
          selectable={true}
          deletable={true}
          draggable={true}
        />
      );

      const select = screen.getByLabelText("Function call for node f1");
      expect(select).toHaveValue("sqrt");

      fireEvent.change(select, { target: { value: "sin" } });
      expect(onChange).toHaveBeenCalledWith("sin");
    });
  });

  describe("EquationRootNode", () => {
    it("renders KaTeX preview and validate button", () => {
      const onValidate = jest.fn();
      render(
        <EquationRootNode
          id="root1"
          data={{ name: "R", latex: "a \\cdot t", onValidate }}
          type="equationRootNode"
          zIndex={1}
          isConnectable={true}
          positionAbsoluteX={0}
          positionAbsoluteY={0}
          selected={false}
          dragging={false}
          selectable={true}
          deletable={true}
          draggable={true}
        />
      );

      expect(screen.getByText(/Equation Root/i)).toBeInTheDocument();
      const validateBtn = screen.getByRole("button", { name: /Validate equation/i });
      fireEvent.click(validateBtn);
      expect(onValidate).toHaveBeenCalledTimes(1);
    });
  });
});
