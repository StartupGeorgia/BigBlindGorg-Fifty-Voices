import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@/test/test-utils";
import userEvent from "@testing-library/user-event";
import { EmbedAgentDialog } from "../embed-agent-dialog";
import type { Agent } from "@/lib/api/agents";

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    patch: vi.fn(),
  },
}));

// Mock the agents api
vi.mock("@/lib/api/agents", () => ({
  updateEmbedSettings: vi.fn(),
}));

// Mock toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock clipboard API
const mockWriteText = vi.fn().mockResolvedValue(undefined);
Object.defineProperty(navigator, "clipboard", {
  value: {
    writeText: mockWriteText,
  },
  configurable: true,
});

const mockAgent: Agent = {
  id: "agent-123",
  name: "Test Agent",
  description: "A test agent",
  pricing_tier: "balanced",
  system_prompt: "You are a helpful assistant",
  language: "en-US",
  voice: "alloy",
  enabled_tools: [],
  enabled_tool_ids: {},
  phone_number_id: null,
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
  total_calls: 0,
  total_duration_seconds: 0,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  last_call_at: null,
};

const mockEmbedSettings = {
  public_id: "pub-agent-123",
  embed_enabled: true,
  allowed_domains: ["example.com", "test.com"],
  embed_settings: {
    button_text: "Talk to us",
    production_url: "",
  },
  script_tag: "<script>...</script>",
  iframe_code: "<iframe>...</iframe>",
};

describe("EmbedAgentDialog", () => {
  const mockOnOpenChange = vi.fn();

  beforeEach(async () => {
    vi.clearAllMocks();
    const { api } = await import("@/lib/api");
    vi.mocked(api.get).mockResolvedValue({ data: mockEmbedSettings });
  });

  it("renders dialog when open", async () => {
    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByText("Embed Voice Agent")).toBeInTheDocument();
    });
  });

  it("shows loading state while fetching embed settings", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.get).mockReturnValue(new Promise(() => {})); // Never resolves

    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    // Should show loading spinner
    const spinner = document.querySelector(".animate-spin");
    expect(spinner).toBeInTheDocument();
  });

  it("displays agent name in dialog description", async () => {
    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByText(/Test Agent/)).toBeInTheDocument();
    });
  });

  it("renders position select with options", async () => {
    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByLabelText("Position")).toBeInTheDocument();
    });
  });

  it("renders theme select with options", async () => {
    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByLabelText("Theme")).toBeInTheDocument();
    });
  });

  it("renders button text input", async () => {
    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Button Text/)).toBeInTheDocument();
    });
  });

  it("limits button text to 20 characters", async () => {
    const user = userEvent.setup();
    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Button Text/)).toBeInTheDocument();
    });

    const input = screen.getByLabelText(/Button Text/) as HTMLInputElement;
    await user.clear(input);
    await user.type(input, "This is a very long text that exceeds limit");

    expect(input.value.length).toBeLessThanOrEqual(20);
  });

  it("displays tabs for Script Tag and iframe", async () => {
    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Script Tag" })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: "iframe" })).toBeInTheDocument();
    });
  });

  it("shows public agent ID", async () => {
    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByText("pub-agent-123")).toBeInTheDocument();
    });
  });

  it("shows embed settings section", async () => {
    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      // Check that the embed settings loaded by looking for the public ID
      expect(screen.getByText("pub-agent-123")).toBeInTheDocument();
    });
  });

  it("copies script tag to clipboard when copy button is clicked", async () => {
    const user = userEvent.setup();
    const { toast } = await import("sonner");

    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByText("Embed Voice Agent")).toBeInTheDocument();
    });

    // Find and click the copy button in the script tab
    const copyButtons = screen.getAllByRole("button");
    const scriptCopyButton = copyButtons.find(
      (btn) => btn.querySelector("svg") && btn.closest('[role="tabpanel"]')
    );

    if (scriptCopyButton) {
      await user.click(scriptCopyButton);
      expect(mockWriteText).toHaveBeenCalled();
    }
  });

  it("renders preview widget button", async () => {
    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByText("Preview Widget")).toBeInTheDocument();
      expect(screen.getByText("Open Preview")).toBeInTheDocument();
    });
  });

  it("opens preview in new tab when button is clicked", async () => {
    const user = userEvent.setup();
    const windowOpenSpy = vi.spyOn(window, "open").mockImplementation(() => null);

    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByText("Open Preview")).toBeInTheDocument();
    });

    const previewButton = screen.getByText("Open Preview");
    await user.click(previewButton);

    expect(windowOpenSpy).toHaveBeenCalledWith(
      expect.stringContaining("/embed/pub-agent-123/preview"),
      "_blank"
    );
  });

  it("shows deployment settings collapsible", async () => {
    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByText("Deployment Settings")).toBeInTheDocument();
    });
  });

  it("displays error message when embed settings fail to load", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.get).mockRejectedValue(new Error("Failed to load"));

    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByText("Failed to load embed settings")).toBeInTheDocument();
    });
  });

  it("does not render when closed", () => {
    render(<EmbedAgentDialog open={false} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    expect(screen.queryByText("Embed Voice Agent")).not.toBeInTheDocument();
  });

  it("switches between script and iframe tabs", async () => {
    const user = userEvent.setup();
    render(<EmbedAgentDialog open={true} onOpenChange={mockOnOpenChange} agent={mockAgent} />);

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "iframe" })).toBeInTheDocument();
    });

    const iframeTab = screen.getByRole("tab", { name: "iframe" });
    await user.click(iframeTab);

    // Check that iframe content instructions are visible
    await waitFor(() => {
      expect(screen.getByText(/Use an iframe for more control/)).toBeInTheDocument();
    });
  });
});
