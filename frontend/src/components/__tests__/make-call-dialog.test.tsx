import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@/test/test-utils";
import userEvent from "@testing-library/user-event";
import { MakeCallDialog } from "../make-call-dialog";
import type { Agent } from "@/lib/api/agents";

// Mock toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock the api module with module-level mock functions
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

// Mock the telephony api
vi.mock("@/lib/api/telephony", () => ({
  initiateCall: vi.fn(),
  hangupCall: vi.fn(),
  listPhoneNumbers: vi.fn(),
}));

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
  total_calls: 0,
  total_duration_seconds: 0,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  last_call_at: null,
};

const mockPhoneNumbers = [
  { id: "phone-123", phone_number: "+15551234567", friendly_name: "Main Line" },
  { id: "phone-456", phone_number: "+15559876543", friendly_name: "Sales" },
];

const mockWorkspaces = [{ workspace_id: "ws-123", workspace_name: "Default Workspace" }];

describe("MakeCallDialog", () => {
  const mockOnOpenChange = vi.fn();

  beforeEach(async () => {
    vi.clearAllMocks();

    // Import mocked modules and configure them
    const { api } = await import("@/lib/api");
    const telephony = await import("@/lib/api/telephony");

    vi.mocked(api.get).mockResolvedValue({ data: mockWorkspaces });
    vi.mocked(telephony.listPhoneNumbers).mockResolvedValue(mockPhoneNumbers);
  });

  it("renders dialog when open", async () => {
    render(
      <MakeCallDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        agent={mockAgent}
        workspaceId="ws-123"
      />
    );

    expect(screen.getByText("Make a Call")).toBeInTheDocument();
  });

  it("displays agent name in dialog description", () => {
    render(
      <MakeCallDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        agent={mockAgent}
        workspaceId="ws-123"
      />
    );

    expect(screen.getByText(/Test Agent/)).toBeInTheDocument();
  });

  it("renders from number label", async () => {
    render(
      <MakeCallDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        agent={mockAgent}
        workspaceId="ws-123"
      />
    );

    // Check for the from number label text rather than form control
    await waitFor(() => {
      expect(screen.getByText("From Number")).toBeInTheDocument();
    });
  });

  it("renders phone number input field", () => {
    render(
      <MakeCallDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        agent={mockAgent}
        workspaceId="ws-123"
      />
    );

    expect(screen.getByLabelText("Phone Number to Call")).toBeInTheDocument();
  });

  it("shows call button in idle state", () => {
    render(
      <MakeCallDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        agent={mockAgent}
        workspaceId="ws-123"
      />
    );

    expect(screen.getByRole("button", { name: /Call/ })).toBeInTheDocument();
  });

  it("shows cancel button in idle state", () => {
    render(
      <MakeCallDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        agent={mockAgent}
        workspaceId="ws-123"
      />
    );

    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("calls onOpenChange when cancel is clicked", async () => {
    const user = userEvent.setup();

    render(
      <MakeCallDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        agent={mockAgent}
        workspaceId="ws-123"
      />
    );

    const cancelButton = screen.getByRole("button", { name: "Cancel" });
    await user.click(cancelButton);

    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it("shows error message when no phone numbers available", async () => {
    const telephony = await import("@/lib/api/telephony");
    vi.mocked(telephony.listPhoneNumbers).mockResolvedValue([]);

    render(
      <MakeCallDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        agent={mockAgent}
        workspaceId="ws-123"
      />
    );

    await waitFor(() => {
      expect(
        screen.getByText("No phone numbers available. Purchase one in Settings.")
      ).toBeInTheDocument();
    });
  });

  it("disables call button when phone number is empty", async () => {
    render(
      <MakeCallDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        agent={mockAgent}
        workspaceId="ws-123"
      />
    );

    await waitFor(() => {
      const callButton = screen.getByRole("button", { name: /Call/ });
      expect(callButton).toBeDisabled();
    });
  });

  it("initiates call when form is valid and call button is clicked", async () => {
    const user = userEvent.setup();
    const telephony = await import("@/lib/api/telephony");

    vi.mocked(telephony.initiateCall).mockResolvedValue({ call_id: "call-123" });

    render(
      <MakeCallDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        agent={mockAgent}
        workspaceId="ws-123"
      />
    );

    // Wait for phone numbers to load (using text check)
    await waitFor(() => {
      expect(screen.getByText("From Number")).toBeInTheDocument();
    });

    // Enter phone number
    const phoneInput = screen.getByLabelText("Phone Number to Call");
    await user.type(phoneInput, "+15551112222");

    // Click call button
    const callButton = screen.getByRole("button", { name: /Call/ });
    await user.click(callButton);

    await waitFor(() => {
      expect(telephony.initiateCall).toHaveBeenCalled();
    });
  });

  it("does not render when closed", () => {
    render(
      <MakeCallDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        agent={mockAgent}
        workspaceId="ws-123"
      />
    );

    expect(screen.queryByText("Make a Call")).not.toBeInTheDocument();
  });

  it("shows E.164 format hint for phone number input", () => {
    render(
      <MakeCallDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        agent={mockAgent}
        workspaceId="ws-123"
      />
    );

    expect(screen.getByText(/E.164 format/)).toBeInTheDocument();
  });
});
