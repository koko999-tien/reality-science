import { ExprNode, VariableSpec } from "@/types/contracts";

export type PresetCategory =
  | "Classical"
  | "Relativistic"
  | "Astrophysics"
  | "Thermodynamics"
  | "Oscillations";

export interface ScientificPreset {
  id: string;
  name: string;
  tagline: string;
  category: PresetCategory;
  formulaLatex: string;
  variables: VariableSpec[];
  ast: ExprNode;
}

export const CANONICAL_PRESETS: ScientificPreset[] = [
  {
    id: "kinematics",
    name: "Kinematics Velocity",
    tagline: "Linear velocity under constant acceleration",
    category: "Classical",
    formulaLatex: "v_0 + a \\cdot t",
    variables: [
      { symbol: "v_0", name: "Initial Velocity", unit: "meter / second", domain: "real", latex_presentation: "v_0" },
      { symbol: "a", name: "Acceleration", unit: "meter / second ** 2", domain: "real", latex_presentation: "a" },
      { symbol: "t", name: "Elapsed Time", unit: "second", domain: "positive_real", latex_presentation: "t" },
    ],
    ast: {
      node_type: "binary_op",
      op: "+",
      left: { node_type: "variable", value: "v_0" },
      right: {
        node_type: "binary_op",
        op: "*",
        left: { node_type: "variable", value: "a" },
        right: { node_type: "variable", value: "t" },
      },
    },
  },
  {
    id: "einstein-energy",
    name: "Einstein Mass-Energy",
    tagline: "Equivalence of relativistic mass and rest energy",
    category: "Relativistic",
    formulaLatex: "m \\cdot c^{2}",
    variables: [
      { symbol: "m", name: "Rest Mass", unit: "kilogram", domain: "positive_real", latex_presentation: "m" },
      { symbol: "c", name: "Speed of Light", unit: "meter / second", domain: "positive_real", latex_presentation: "c" },
    ],
    ast: {
      node_type: "binary_op",
      op: "*",
      left: { node_type: "variable", value: "m" },
      right: {
        node_type: "binary_op",
        op: "**",
        left: { node_type: "variable", value: "c" },
        right: { node_type: "constant", value: 2 },
      },
    },
  },
  {
    id: "newton-gravity",
    name: "Newton's Gravity",
    tagline: "Universal gravitational attraction between masses",
    category: "Astrophysics",
    formulaLatex: "\\frac{G \\cdot (m_1 \\cdot m_2)}{r^{2}}",
    variables: [
      { symbol: "G", name: "Gravitational Constant", unit: "meter ** 3 / (kilogram * second ** 2)", domain: "positive_real", latex_presentation: "G" },
      { symbol: "m_1", name: "Mass 1", unit: "kilogram", domain: "positive_real", latex_presentation: "m_1" },
      { symbol: "m_2", name: "Mass 2", unit: "kilogram", domain: "positive_real", latex_presentation: "m_2" },
      { symbol: "r", name: "Radial Distance", unit: "meter", domain: "positive_real", latex_presentation: "r" },
    ],
    ast: {
      node_type: "binary_op",
      op: "/",
      left: {
        node_type: "binary_op",
        op: "*",
        left: { node_type: "variable", value: "G" },
        right: {
          node_type: "binary_op",
          op: "*",
          left: { node_type: "variable", value: "m_1" },
          right: { node_type: "variable", value: "m_2" },
        },
      },
      right: {
        node_type: "binary_op",
        op: "**",
        left: { node_type: "variable", value: "r" },
        right: { node_type: "constant", value: 2 },
      },
    },
  },
  {
    id: "kinetic-energy",
    name: "Kinetic Energy",
    tagline: "Work required to accelerate a body of mass m",
    category: "Classical",
    formulaLatex: "(0.5 \\cdot m) \\cdot v^{2}",
    variables: [
      { symbol: "m", name: "Mass", unit: "kilogram", domain: "positive_real", latex_presentation: "m" },
      { symbol: "v", name: "Velocity", unit: "meter / second", domain: "real", latex_presentation: "v" },
    ],
    ast: {
      node_type: "binary_op",
      op: "*",
      left: {
        node_type: "binary_op",
        op: "*",
        left: { node_type: "constant", value: 0.5 },
        right: { node_type: "variable", value: "m" },
      },
      right: {
        node_type: "binary_op",
        op: "**",
        left: { node_type: "variable", value: "v" },
        right: { node_type: "constant", value: 2 },
      },
    },
  },
  {
    id: "ideal-gas",
    name: "Ideal Gas Law",
    tagline: "State of an ideal gas relating P, V, n, R, T",
    category: "Thermodynamics",
    formulaLatex: "\\frac{(n \\cdot R) \\cdot T}{V}",
    variables: [
      { symbol: "n", name: "Amount of Substance", unit: "mole", domain: "positive_real", latex_presentation: "n" },
      { symbol: "R", name: "Gas Constant", unit: "joule / (kelvin * mole)", domain: "positive_real", latex_presentation: "R" },
      { symbol: "T", name: "Absolute Temperature", unit: "kelvin", domain: "positive_real", latex_presentation: "T" },
      { symbol: "V", name: "Volume", unit: "meter ** 3", domain: "positive_real", latex_presentation: "V" },
    ],
    ast: {
      node_type: "binary_op",
      op: "/",
      left: {
        node_type: "binary_op",
        op: "*",
        left: {
          node_type: "binary_op",
          op: "*",
          left: { node_type: "variable", value: "n" },
          right: { node_type: "variable", value: "R" },
        },
        right: { node_type: "variable", value: "T" },
      },
      right: { node_type: "variable", value: "V" },
    },
  },
  {
    id: "harmonic-oscillator",
    name: "Harmonic Oscillator Energy",
    tagline: "Potential energy stored in a Hookean spring",
    category: "Oscillations",
    formulaLatex: "(0.5 \\cdot k) \\cdot x^{2}",
    variables: [
      { symbol: "k", name: "Spring Constant", unit: "newton / meter", domain: "positive_real", latex_presentation: "k" },
      { symbol: "x", name: "Displacement", unit: "meter", domain: "real", latex_presentation: "x" },
    ],
    ast: {
      node_type: "binary_op",
      op: "*",
      left: {
        node_type: "binary_op",
        op: "*",
        left: { node_type: "constant", value: 0.5 },
        right: { node_type: "variable", value: "k" },
      },
      right: {
        node_type: "binary_op",
        op: "**",
        left: { node_type: "variable", value: "x" },
        right: { node_type: "constant", value: 2 },
      },
    },
  },
];
