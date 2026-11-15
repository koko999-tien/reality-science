import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  ScientificPresetDemo,
  SCIENTIFIC_PRESETS,
} from "@/components/home/ScientificPresetDemo";
import { FeaturePillars, FEATURE_PILLARS } from "@/components/home/FeaturePillars";
import { WorkflowTour, WORKFLOW_STEPS } from "@/components/home/WorkflowTour";
import HomePage from "@/app/page";

describe("Milestone 2 Home Components & Landing Page", () => {
  describe("ScientificPresetDemo", () => {
    it("renders the 1-click presets demo widget with default Kinematics preset", () => {
      render(<ScientificPresetDemo />);

      expect(screen.getByTestId("scientific-preset-demo")).toBeInTheDocument();
      expect(
        screen.getByText(/1-Click Scientific Presets Verification/i)
      ).toBeInTheDocument();
      expect(screen.getByText("Kinematics Velocity")).toBeInTheDocument();

      // Check default verdict badge
      const verdict = screen.getByTestId("preset-verdict-badge");
      expect(verdict).toHaveTextContent("PASS");
    });

    it("displays all 4 scientific presets in tablist", () => {
      render(<ScientificPresetDemo />);

      const tabs = screen.getAllByRole("tab");
      expect(tabs).toHaveLength(4);

      expect(screen.getByRole("tab", { name: /Kinematics/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Einstein/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Newtonian/i })).toBeInTheDocument();
      expect(
        screen.getByRole("tab", { name: /Dimensional Invariant Violation/i })
      ).toBeInTheDocument();
    });

    it("switches to Einstein Mass-Energy preset and renders relativistic metrics", () => {
      render(<ScientificPresetDemo />);

      const einsteinTab = screen.getByRole("tab", { name: /Einstein/i });
      fireEvent.click(einsteinTab);

      expect(
        screen.getByText(/Lorentz-Poincaré Mass-Energy Equivalence Verified/i)
      ).toBeInTheDocument();
      expect(screen.getByTestId("preset-verdict-badge")).toHaveTextContent("PASS");
    });

    it("switches to Newtonian Gravity preset and renders celestial mechanics metrics", () => {
      render(<ScientificPresetDemo />);

      const gravityTab = screen.getByRole("tab", { name: /Newtonian/i });
      fireEvent.click(gravityTab);

      expect(
        screen.getByText(/Inverse-Square Law & Universal Gravitation Verified/i)
      ).toBeInTheDocument();
      expect(screen.getByTestId("preset-verdict-badge")).toHaveTextContent("PASS");
    });

    it("detects dimensional mismatch and displays FAIL for the negative control preset", () => {
      render(<ScientificPresetDemo />);

      const negativeTab = screen.getByRole("tab", {
        name: /Dimensional Invariant Violation/i,
      });
      fireEvent.click(negativeTab);

      // Must show FAIL verdict
      expect(screen.getByTestId("preset-verdict-badge")).toHaveTextContent("FAIL");
      expect(
        screen.getByText(/FAIL at Layer 3: Dimensional Homogeneity Violation/i)
      ).toBeInTheDocument();

      // Check layer 3 failure card
      const layer3 = screen.getByTestId("preset-layer-3");
      expect(layer3).toHaveTextContent(/Incompatible dimensions/i);
      expect(layer3).toHaveTextContent("FAIL");

      // Check subsequent layers blocked
      const layer4 = screen.getByTestId("preset-layer-4");
      expect(layer4).toHaveTextContent("BLOCKED");
    });

    it("toggles between 6-Layer Verification Pipeline and Declared Physical Quantities tabs", () => {
      render(<ScientificPresetDemo />);

      const variablesTab = screen.getByRole("button", {
        name: /Declared Physical Quantities/i,
      });
      fireEvent.click(variablesTab);

      expect(screen.getByText("Fundamental Dimensions")).toBeInTheDocument();
      expect(screen.getByText("Final Velocity")).toBeInTheDocument();
      expect(screen.getByText("Elapsed Time")).toBeInTheDocument();

      const layersTab = screen.getByRole("button", {
        name: /6-Layer Verification Pipeline/i,
      });
      fireEvent.click(layersTab);

      expect(screen.getByTestId("preset-layer-1")).toBeInTheDocument();
      expect(screen.getByTestId("preset-layer-6")).toBeInTheDocument();
    });

    it("provides direct CTA link to Studio Canvas with preset parameter", () => {
      render(<ScientificPresetDemo />);

      const ctaLink = screen.getByRole("link", {
        name: /Load this Model into Canvas Studio/i,
      });
      expect(ctaLink).toHaveAttribute(
        "href",
        expect.stringMatching(/\/projects\/default-model\/editor\?preset=/)
      );
    });
  });

  describe("FeaturePillars", () => {
    it("renders all 4 architectural feature pillars", () => {
      render(<FeaturePillars />);

      expect(
        screen.getByText(/Engineered for Mathematical Truth & Physical Rigor/i)
      ).toBeInTheDocument();

      expect(screen.getByTestId("feature-pillar-pillar-6-layer")).toBeInTheDocument();
      expect(
        screen.getByTestId("feature-pillar-pillar-zero-trust")
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("feature-pillar-pillar-flow-canvas")
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("feature-pillar-pillar-crypto-bundles")
      ).toBeInTheDocument();
    });

    it("displays technical specifications and capabilities in each pillar", () => {
      render(<FeaturePillars />);

      expect(
        screen.getByText(/ADR-001 Zero-Trust Compute Isolation/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Reactive AST Flow Canvas/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Cryptographic Verification Bundles/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/6-Layer Epistemic Verification Pipeline/i)
      ).toBeInTheDocument();
    });
  });

  describe("WorkflowTour", () => {
    it("renders the 4-step scientific workflow tour", () => {
      render(<WorkflowTour />);

      expect(
        screen.getByText(/From Intuition to Mathematically Proven Reality/i)
      ).toBeInTheDocument();

      const tabs = screen.getAllByRole("tab");
      expect(tabs).toHaveLength(4);

      expect(screen.getByTestId("mockup-variables")).toBeInTheDocument();
    });

    it("cycles through steps on tab click and next step button", () => {
      render(<WorkflowTour />);

      // Click step 2
      const step2Tab = screen.getByRole("tab", {
        name: /Compose Equation Nodes/i,
      });
      fireEvent.click(step2Tab);
      expect(screen.getByTestId("mockup-canvas")).toBeInTheDocument();

      // Click step 3
      const step3Tab = screen.getByRole("tab", {
        name: /Execute 6-Layer Multi-Stage Truth Verification/i,
      });
      fireEvent.click(step3Tab);
      expect(screen.getByTestId("mockup-verification")).toBeInTheDocument();

      // Click step 4
      const step4Tab = screen.getByRole("tab", {
        name: /Export Cryptographically Signed Preprint Bundle/i,
      });
      fireEvent.click(step4Tab);
      expect(screen.getByTestId("mockup-bundle")).toBeInTheDocument();

      // Click Next Step (should wrap back to Step 1)
      const nextBtn = screen.getByRole("button", { name: /Next Step/i });
      fireEvent.click(nextBtn);
      expect(screen.getByTestId("mockup-variables")).toBeInTheDocument();
    });
  });

  describe("HomePage Integration", () => {
    it("renders the complete futuristic landing page with all sub-components", () => {
      render(<HomePage />);

      // Hero elements
      expect(
        screen.getByText(/Epistemic Physics & Mathematical Verification Engine v1.0/i)
      ).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { level: 1 })
      ).toHaveTextContent(/REALITY SCIENCE/i);
      expect(
        screen.getByText(/Evidence-Driven Scientific Hypothesis & Mathematical Verification Engine/i)
      ).toBeInTheDocument();

      // Main CTA
      const mainCta = screen.getByRole("link", { name: /^Launch Studio Canvas$/i });
      expect(mainCta).toHaveAttribute("href", "/projects/default-model/editor");

      // Embedded sections
      expect(screen.getByTestId("scientific-preset-demo")).toBeInTheDocument();
      expect(
        screen.getByTestId("feature-pillar-pillar-6-layer")
      ).toBeInTheDocument();
      expect(
        screen.getByText(/From Intuition to Mathematically Proven Reality/i)
      ).toBeInTheDocument();

      // Footer
      expect(screen.getByText(/MIT Open Source License/i)).toBeInTheDocument();
      expect(screen.getByText(/Deployed on Vercel Edge Runtime/i)).toBeInTheDocument();
      expect(screen.getByText(/Developer & Headless API Note/i)).toBeInTheDocument();
    });
  });
});
