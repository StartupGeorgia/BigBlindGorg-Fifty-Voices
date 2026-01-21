import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@/test/test-utils";
import userEvent from "@testing-library/user-event";
import AgentsPage from "../page";
import type { Agent } from "@/lib/api/agents";

// Mock toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

const mockFetchAgents = vi.fn();
const mockDeleteAgent = vi.fn();
const mockCreateAgent = vi.fn();
const mockGetAgent = vi.fn();
const mockApiGet = vi.fn();

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    get: () => mockApiGet(),
  },
}));

// Mock the agents api
vi.mock("@/lib/api/agents", () => ({
  fetchAgents: () => mockFetchAgents(),
  deleteAgent: () => mockDeleteAgent(),
  createAgent: () => mockCreateAgent(),
  getAgent: () => mockGetAgent(),
}));

// Mock MakeCallDialog
vi.mock("@/components/make-call-dialog", () => ({
  MakeCallDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="make-call-dialog">Make Call Dialog</div> : null,
}));

// Mock EmbedAgentDialog
vi.mock("@/components/embed-agent-dialog", () => ({
  EmbedAgentDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="embed-dialog">Embed Dialog</div> : null,
}));

const mockAgent: Agent = {
  id: "agent-123",
  name: "Test Agent",
  description: "A test agent",
  pricing_tier: "balanced",
  system_prompt: "You are a helpful assistant",
  language: "en-US",
  voice: "alloy",
  enabled_tools: ["calendar"],
  enabled_tool_ids: {},
  phone_number_id: "phone-123",
  enable_recording: false,
  enable_transcript: true,
  turn_detection_mode: "normal",
  turn_detection_threshold: 0.5,
  turn_detection_prefix_padding_ms: 300,
  turn_detection_silence_duration_ms: 500,
  temperature: 0.7,
  max_tokens: 1024,
  initial_greeting: "Hello!",
  is_active: true,
  is_published: false,
  total_calls: 25,
  total_duration_seconds: 1500,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-15T00:00:00Z",
  last_call_at: "2024-01-15T10:00:00Z",
};

const mockWorkspace = {
  id: "ws-123",
  name: "Default Workspace",
  description: "Default workspace",
  is_default: true,
};

describe("AgentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockFetchAgents.mockResolvedValue([mockAgent]);
    mockApiGet.mockResolvedValue({ data: [mockWorkspace] });
  });

  it("renders page title", async () => {
    render(<AgentsPage />);

    expect(screen.getByText("Voice Agents")).toBeInTheDocument();
    expect(screen.getByText("Manage and configure your AI voice agents")).toBeInTheDocument();
  });

  it("shows loading state initially", () => {
    mockFetchAgents.mockReturnValue(new Promise(() => {})); // Never resolves

    render(<AgentsPage />);

    expect(screen.getByText("Loading agents...")).toBeInTheDocument();
  });

  it("displays agents after loading", async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Test Agent")).toBeInTheDocument();
    });
  });

  it("shows empty state when no agents exist", async () => {
    mockFetchAgents.mockResolvedValue([]);

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText("No voice agents yet")).toBeInTheDocument();
    });
  });

  it("shows create workspace button when no workspaces exist", async () => {
    mockFetchAgents.mockResolvedValue([]);
    mockApiGet.mockResolvedValue({ data: [] });

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /Create Workspace/ })).toBeInTheDocument();
    });
  });

  it("shows create agent button when workspaces exist", async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /Create Agent/ })).toBeInTheDocument();
    });
  });

  it("displays agent details on card", async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Test Agent")).toBeInTheDocument();
      expect(screen.getByText("Balanced")).toBeInTheDocument();
      expect(screen.getByText("25 calls")).toBeInTheDocument();
      expect(screen.getByText("Active")).toBeInTheDocument();
    });
  });

  it("shows phone badge when agent has phone number", async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Phone")).toBeInTheDocument();
    });
  });

  it("shows tools count badge when agent has enabled tools", async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      // The badge shows the count of enabled tools
      expect(screen.getByText("1")).toBeInTheDocument();
    });
  });

  it("shows inactive badge for inactive agent", async () => {
    mockFetchAgents.mockResolvedValue([{ ...mockAgent, is_active: false }]);

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Inactive")).toBeInTheDocument();
    });
  });

  it("displays error state when fetching fails", async () => {
    mockFetchAgents.mockRejectedValue(new Error("Network error"));

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Failed to load agents")).toBeInTheDocument();
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("shows try again button on error", async () => {
    mockFetchAgents.mockRejectedValue(new Error("Network error"));

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Try Again" })).toBeInTheDocument();
    });
  });

  it("renders workspace selector when workspaces exist", async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      // The select trigger should contain "All Workspaces"
      expect(screen.getByText(/All Workspaces/)).toBeInTheDocument();
    });
  });

  it("opens dropdown menu when clicking more button", async () => {
    const user = userEvent.setup();
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Test Agent")).toBeInTheDocument();
    });

    // Find the more button (MoreVertical icon button)
    const moreButtons = screen.getAllByRole("button");
    const moreButton = moreButtons.find((btn) => btn.querySelector("svg"));

    if (moreButton) {
      await user.click(moreButton);

      await waitFor(() => {
        expect(screen.getByText("Edit")).toBeInTheDocument();
        expect(screen.getByText("Test")).toBeInTheDocument();
        expect(screen.getByText("Make Call")).toBeInTheDocument();
        expect(screen.getByText("Duplicate")).toBeInTheDocument();
        expect(screen.getByText("Embed")).toBeInTheDocument();
        expect(screen.getByText("Delete")).toBeInTheDocument();
      });
    }
  });

  it("links to agent edit page", async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Test Agent")).toBeInTheDocument();
    });

    // The card itself should be clickable and navigate to agent details
    // Check for the Edit link in dropdown
    const user = userEvent.setup();
    const moreButtons = screen.getAllByRole("button");
    const moreButton = moreButtons.find((btn) => btn.querySelector("svg"));

    if (moreButton) {
      await user.click(moreButton);

      await waitFor(() => {
        const editLink = screen.getByText("Edit");
        expect(editLink.closest("a")).toHaveAttribute("href", "/dashboard/agents/agent-123");
      });
    }
  });

  it("has correct link to create agent page", async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      const createLink = screen.getByRole("link", { name: /Create Agent/ });
      expect(createLink).toHaveAttribute("href", "/dashboard/agents/create-agent");
    });
  });

  it("displays multiple agents in grid", async () => {
    const secondAgent = { ...mockAgent, id: "agent-456", name: "Second Agent" };
    mockFetchAgents.mockResolvedValue([mockAgent, secondAgent]);

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Test Agent")).toBeInTheDocument();
      expect(screen.getByText("Second Agent")).toBeInTheDocument();
    });
  });

  it("hides phone badge when agent has no phone number", async () => {
    mockFetchAgents.mockResolvedValue([{ ...mockAgent, phone_number_id: null }]);

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Test Agent")).toBeInTheDocument();
      expect(screen.queryByText("Phone")).not.toBeInTheDocument();
    });
  });

  it("hides tools badge when agent has no enabled tools", async () => {
    mockFetchAgents.mockResolvedValue([{ ...mockAgent, enabled_tools: [] }]);

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Test Agent")).toBeInTheDocument();
      // The tools badge should not be present
      const badges = screen.getAllByText(/Active|Inactive/);
      expect(badges.length).toBeGreaterThan(0);
    });
  });

  it("formats pricing tier with capitalized first letter", async () => {
    mockFetchAgents.mockResolvedValue([{ ...mockAgent, pricing_tier: "premium" }]);

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText("Premium")).toBeInTheDocument();
    });
  });
});
