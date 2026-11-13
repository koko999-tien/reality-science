import React from "react";
import katex from "katex";

interface KatexFormulaProps {
  math: string;
  block?: boolean;
}

export const KatexFormula: React.FC<KatexFormulaProps> = ({ math, block = false }) => {
  const html = katex.renderToString(math, {
    displayMode: block,
    throwOnError: false,
  });

  return <span dangerouslySetInnerHTML={{ __html: html }} />;
};
