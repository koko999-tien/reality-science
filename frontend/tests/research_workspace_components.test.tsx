import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ResearchProjectLookup } from "@/components/home/ResearchProjectLookup";
import { ScientificModelExample } from "@/components/home/ScientificModelExample";
import ProjectsDashboardPage from "@/app/(dashboard)/projects/page";
import { fetchProjectBySlug } from "@/lib/api";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("@/lib/api", () => ({
  fetchProjectBySlug: jest.fn(),
}));

describe("research workspace components", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("opens only a project record returned by the API", async () => {
    (fetchProjectBySlug as jest.Mock).mockResolvedValue({ slug: "lab-kinematics" });
    render(<ResearchProjectLookup />);

    fireEvent.change(screen.getByRole("textbox", { name: "Project identifier" }), {
      target: { value: "lab-kinematics" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Open project" }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/projects/lab-kinematics"));
    expect(fetchProjectBySlug).toHaveBeenCalledWith("lab-kinematics");
  });

  it("shows the API failure and does not navigate to a fabricated project", async () => {
    (fetchProjectBySlug as jest.Mock).mockRejectedValue(new Error("Project not found"));
    render(<ResearchProjectLookup />);

    fireEvent.change(screen.getByRole("textbox", { name: "Project identifier" }), {
      target: { value: "missing-project" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Open project" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Project not found");
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("keeps the project catalog API-backed without static verification claims", () => {
    render(<ProjectsDashboardPage />);

    expect(screen.getByRole("heading", { name: "Open a scientific project" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Project identifier" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Open project" })).toHaveLength(1);
    expect(screen.queryByText("Verified", { exact: true })).not.toBeInTheDocument();
    expect(screen.queryByText("PASS", { exact: true })).not.toBeInTheDocument();
  });

  it("labels examples as illustrative and switches dimensional examples without a verdict", () => {
    render(<ScientificModelExample />);

    expect(screen.getByText(/Illustrative examples · no validation run/i)).toBeInTheDocument();
    expect(screen.getByText("v = v₀ + at")).toBeInTheDocument();
    expect(screen.queryByText("PASS")).not.toBeInTheDocument();
    expect(screen.queryByText(/NIST|measured|verified/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Incompatible sum" }));
    expect(screen.getByText("x + t")).toBeInTheDocument();
    expect(screen.getByText("[L] + [T] is dimensionally incompatible")).toBeInTheDocument();
    expect(screen.getByText(/not a scientific result/i)).toBeInTheDocument();
  });

  it("supports arrow, Home, and End keyboard navigation in the landing example tabs", () => {
    render(<ScientificModelExample />);
    const kinematicsTab = screen.getByRole("tab", { name: "Kinematics" });
    const forceTab = screen.getByRole("tab", { name: "Newton's second law" });
    const incompatibleTab = screen.getByRole("tab", { name: "Incompatible sum" });

    fireEvent.keyDown(kinematicsTab, { key: "ArrowRight" });
    expect(forceTab).toHaveAttribute("aria-selected", "true");
    expect(forceTab).toHaveFocus();
    fireEvent.keyDown(forceTab, { key: "ArrowRight" });
    expect(incompatibleTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "Incompatible sum" })).toBeInTheDocument();
    fireEvent.keyDown(incompatibleTab, { key: "ArrowRight" });
    expect(kinematicsTab).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(kinematicsTab, { key: "ArrowLeft" });
    expect(incompatibleTab).toHaveFocus();
    fireEvent.keyDown(incompatibleTab, { key: "Home" });
    expect(kinematicsTab).toHaveFocus();
    fireEvent.keyDown(kinematicsTab, { key: "End" });
    expect(incompatibleTab).toHaveFocus();
  });
});
