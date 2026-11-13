import React from "react";
import { render } from "@testing-library/react";
import { KatexFormula } from "../src/components/equations/KatexFormula";

describe("KatexFormula Component", () => {
  it("renders formula without throwing", () => {
    const { container } = render(<KatexFormula math="E = mc^2" />);
    expect(container.querySelector(".katex")).not.toBeNull();
  });
});
