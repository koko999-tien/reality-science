import React from "react";
import { render } from "@testing-library/react";
import { AstVisualizer } from "../src/components/equations/AstVisualizer";
import { ExprNode } from "../src/types/contracts";

describe("AstVisualizer Component", () => {
  it("renders AST node content properly", () => {
    const node: ExprNode = {
      node_type: "constant",
      value: 42,
    };
    const { getByText } = render(<AstVisualizer ast={node} />);
    expect(getByText(/AST Node: constant/)).toBeInTheDocument();
  });
});
