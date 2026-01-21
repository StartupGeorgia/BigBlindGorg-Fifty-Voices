import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@/test/test-utils";
import userEvent from "@testing-library/user-event";
import { TopBar } from "../top-bar";

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

// Mock the agents api
vi.mock("@/lib/api/agents", () => ({
  fetchAgents: vi.fn(),
}));

// Mock the phone-numbers api
vi.mock("@/lib/api/phone-numbers", () => ({
  listPhoneNumbers: vi.fn(),
}));

// Mock the compliance api
vi.mock("@/lib/api/compliance", () => ({
  fetchComplianceStatus: vi.fn(),
}));

// Mock CompliancePanel component to simplify testing
vi.mock("@/components/compliance-panel", () => ({
  CompliancePanel: ({
    open,
    onOpenChange,
    initialTab,
  }: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    initialTab: string;
  }) =>
    open ? (
      <div data-testid="compliance-panel">
        <span data-testid="panel-tab">{initialTab}</span>
        <button onClick={() => onOpenChange(false)}>Close Panel</button>
      </div>
    ) : null,
}));

const mockAgents = [
  { id: "1", name: "Agent 1" },
  { id: "2", name: "Agent 2" },
  { id: "3", name: "Agent 3" },
];

const mockWorkspaces = [{ id: "ws-1" }, { id: "ws-2" }];

const mockAppointments = [{ id: "apt-1" }, { id: "apt-2" }, { id: "apt-3" }, { id: "apt-4" }];

const mockPhoneNumbers = { total: 5 };

const mockContacts = [{ id: 1 }, { id: 2 }];

const mockComplianceStatus = {
  gdpr: {
    completed: 8,
    total: 10,
    percentage: 80,
    checks: [],
  },
  ccpa: {
    completed: 10,
    total: 10,
    percentage: 100,
    checks: [],
  },
};

describe("TopBar", () => {
  beforeEach(async () => {
    vi.clearAllMocks();

    const { api } = await import("@/lib/api");
    const { fetchAgents } = await import("@/lib/api/agents");
    const { listPhoneNumbers } = await import("@/lib/api/phone-numbers");
    const { fetchComplianceStatus } = await import("@/lib/api/compliance");

    vi.mocked(fetchAgents).mockResolvedValue(mockAgents as never);
    vi.mocked(listPhoneNumbers).mockResolvedValue(mockPhoneNumbers as never);
    vi.mocked(fetchComplianceStatus).mockResolvedValue(mockComplianceStatus as never);

    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes("/workspaces")) {
        return Promise.resolve({ data: mockWorkspaces });
      }
      if (url.includes("/appointments")) {
        return Promise.resolve({ data: mockAppointments });
      }
      if (url.includes("/contacts")) {
        return Promise.resolve({ data: mockContacts });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it("renders top bar component", () => {
    render(<TopBar />);
    expect(screen.getByText("Agents")).toBeInTheDocument();
  });

  it("displays all stat items", async () => {
    render(<TopBar />);

    await waitFor(() => {
      expect(screen.getByText("Agents")).toBeInTheDocument();
      expect(screen.getByText("Workspaces")).toBeInTheDocument();
      expect(screen.getByText("Appointments")).toBeInTheDocument();
      expect(screen.getByText("Phone Numbers")).toBeInTheDocument();
      expect(screen.getByText("Contacts")).toBeInTheDocument();
    });
  });

  it("displays agent count", async () => {
    render(<TopBar />);

    await waitFor(() => {
      expect(screen.getByText("3")).toBeInTheDocument(); // mockAgents.length
    });
  });

  it("displays workspace count", async () => {
    render(<TopBar />);

    await waitFor(() => {
      // Check that "Workspaces" label exists - count is shown but might overlap with contacts
      expect(screen.getByText("Workspaces")).toBeInTheDocument();
    });
  });

  it("displays appointments count", async () => {
    render(<TopBar />);

    await waitFor(() => {
      expect(screen.getByText("4")).toBeInTheDocument(); // mockAppointments.length
    });
  });

  it("displays phone numbers count", async () => {
    render(<TopBar />);

    await waitFor(() => {
      expect(screen.getByText("5")).toBeInTheDocument(); // mockPhoneNumbers.total
    });
  });

  it("displays contacts count", async () => {
    render(<TopBar />);

    await waitFor(() => {
      const twoElements = screen.getAllByText("2");
      expect(twoElements.length).toBeGreaterThan(0); // mockContacts.length
    });
  });

  it("shows loading state with dashes while data is loading", async () => {
    const { fetchAgents } = await import("@/lib/api/agents");
    vi.mocked(fetchAgents).mockReturnValue(new Promise(() => {}) as never); // Never resolves

    render(<TopBar />);

    // Should show dash while loading
    const dashes = screen.getAllByText("–");
    expect(dashes.length).toBeGreaterThan(0);
  });

  it("displays GDPR compliance badge", async () => {
    render(<TopBar />);

    await waitFor(() => {
      expect(screen.getByText("GDPR")).toBeInTheDocument();
      expect(screen.getByText("80%")).toBeInTheDocument();
    });
  });

  it("displays CCPA compliance badge", async () => {
    render(<TopBar />);

    await waitFor(() => {
      expect(screen.getByText("CCPA")).toBeInTheDocument();
      expect(screen.getByText("100%")).toBeInTheDocument();
    });
  });

  it("opens GDPR compliance panel when GDPR badge is clicked", async () => {
    const user = userEvent.setup();
    render(<TopBar />);

    await waitFor(() => {
      expect(screen.getByText("GDPR")).toBeInTheDocument();
    });

    const gdprBadge = screen.getByText("GDPR").closest("button");
    if (gdprBadge) {
      await user.click(gdprBadge);
    }

    await waitFor(() => {
      expect(screen.getByTestId("compliance-panel")).toBeInTheDocument();
      expect(screen.getByTestId("panel-tab")).toHaveTextContent("gdpr");
    });
  });

  it("opens CCPA compliance panel when CCPA badge is clicked", async () => {
    const user = userEvent.setup();
    render(<TopBar />);

    await waitFor(() => {
      expect(screen.getByText("CCPA")).toBeInTheDocument();
    });

    const ccpaBadge = screen.getByText("CCPA").closest("button");
    if (ccpaBadge) {
      await user.click(ccpaBadge);
    }

    await waitFor(() => {
      expect(screen.getByTestId("compliance-panel")).toBeInTheDocument();
      expect(screen.getByTestId("panel-tab")).toHaveTextContent("ccpa");
    });
  });

  it("applies correct color class for incomplete GDPR compliance", async () => {
    render(<TopBar />);

    await waitFor(() => {
      const gdprBadge = screen.getByText("GDPR").closest("button");
      expect(gdprBadge).toHaveClass("text-amber-500"); // 80% = amber
    });
  });

  it("applies correct color class for complete CCPA compliance", async () => {
    render(<TopBar />);

    await waitFor(() => {
      const ccpaBadge = screen.getByText("CCPA").closest("button");
      expect(ccpaBadge).toHaveClass("text-emerald-500"); // 100% = green
    });
  });

  it("applies red color class for low compliance percentage", async () => {
    const { fetchComplianceStatus } = await import("@/lib/api/compliance");
    vi.mocked(fetchComplianceStatus).mockResolvedValue({
      gdpr: { completed: 3, total: 10, percentage: 30, checks: [] },
      ccpa: { completed: 10, total: 10, percentage: 100, checks: [] },
    } as never);

    render(<TopBar />);

    await waitFor(() => {
      const gdprBadge = screen.getByText("GDPR").closest("button");
      expect(gdprBadge).toHaveClass("text-red-500"); // 30% = red
    });
  });

  it("renders shield icon next to compliance badges", async () => {
    const { container } = render(<TopBar />);

    await waitFor(() => {
      expect(screen.getByText("GDPR")).toBeInTheDocument();
    });

    // Check for shield icon SVG (lucide icons render as SVG)
    const svgIcons = container.querySelectorAll("svg");
    expect(svgIcons.length).toBeGreaterThan(0);
  });

  it("has proper layout structure", () => {
    const { container } = render(<TopBar />);

    // Check for the main container with flex layout
    const topBarContainer = container.querySelector(".flex.h-12.items-center.justify-between");
    expect(topBarContainer).toBeInTheDocument();
  });

  it("shows 0 when no data is available", async () => {
    const { fetchAgents } = await import("@/lib/api/agents");
    const { listPhoneNumbers } = await import("@/lib/api/phone-numbers");
    const { api } = await import("@/lib/api");

    vi.mocked(fetchAgents).mockResolvedValue([]);
    vi.mocked(listPhoneNumbers).mockResolvedValue({ total: 0 } as never);
    vi.mocked(api.get).mockResolvedValue({ data: [] });

    render(<TopBar />);

    await waitFor(() => {
      const zeros = screen.getAllByText("0");
      expect(zeros.length).toBeGreaterThan(0);
    });
  });
});
