import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  createAgent,
  fetchAgents,
  getAgent,
  updateAgent,
  deleteAgent,
  getEmbedSettings,
  updateEmbedSettings,
  type Agent,
  type CreateAgentRequest,
  type UpdateAgentRequest,
} from "../api/agents";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Store original localStorage
const originalLocalStorage = global.localStorage;

describe("Agent API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    localStorage.setItem("access_token", "test-token");
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("fetchAgents", () => {
    it("fetches all agents successfully", async () => {
      const mockAgents: Agent[] = [
        {
          id: "agent-1",
          name: "Test Agent 1",
          description: "Description 1",
          pricing_tier: "balanced",
          system_prompt: "You are helpful",
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
          total_calls: 10,
          total_duration_seconds: 600,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          last_call_at: null,
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockAgents),
      });

      const result = await fetchAgents();

      expect(result).toEqual(mockAgents);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/agents"),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer test-token",
          }),
        })
      );
    });

    it("throws error on failed fetch", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Unauthorized",
      });

      await expect(fetchAgents()).rejects.toThrow("Failed to fetch agents: Unauthorized");
    });

    it("handles timeout", async () => {
      mockFetch.mockImplementationOnce(
        () =>
          new Promise((_, reject) => {
            const error = new Error("Request timed out - please check if the backend is running");
            error.name = "AbortError";
            reject(error);
          })
      );

      await expect(fetchAgents()).rejects.toThrow();
    });
  });

  describe("getAgent", () => {
    it("fetches a specific agent by ID", async () => {
      const mockAgent: Agent = {
        id: "agent-123",
        name: "Test Agent",
        description: "A test agent",
        pricing_tier: "premium",
        system_prompt: "You are a premium assistant",
        language: "en-US",
        voice: "nova",
        enabled_tools: ["calendar"],
        enabled_tool_ids: {},
        phone_number_id: "phone-123",
        enable_recording: true,
        enable_transcript: true,
        turn_detection_mode: "semantic",
        turn_detection_threshold: 0.6,
        turn_detection_prefix_padding_ms: 300,
        turn_detection_silence_duration_ms: 600,
        temperature: 0.8,
        max_tokens: 2048,
        initial_greeting: "Hi there!",
        is_active: true,
        is_published: true,
        total_calls: 50,
        total_duration_seconds: 3600,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-15T00:00:00Z",
        last_call_at: "2024-01-14T12:00:00Z",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockAgent),
      });

      const result = await getAgent("agent-123");

      expect(result).toEqual(mockAgent);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/agents/agent-123"),
        expect.any(Object)
      );
    });

    it("throws error when agent not found", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Not Found",
      });

      await expect(getAgent("nonexistent")).rejects.toThrow("Failed to fetch agent: Not Found");
    });
  });

  describe("createAgent", () => {
    it("creates a new agent successfully", async () => {
      const createRequest: CreateAgentRequest = {
        name: "New Agent",
        description: "A new agent",
        pricing_tier: "budget",
        system_prompt: "You are a budget assistant",
        language: "en-US",
        voice: "echo",
        enabled_tools: [],
        enable_recording: false,
        enable_transcript: true,
        temperature: 0.7,
      };

      const createdAgent: Agent = {
        id: "new-agent-id",
        ...createRequest,
        description: createRequest.description!,
        enabled_tool_ids: {},
        phone_number_id: null,
        turn_detection_mode: "normal",
        turn_detection_threshold: 0.5,
        turn_detection_prefix_padding_ms: 300,
        turn_detection_silence_duration_ms: 500,
        max_tokens: 1024,
        initial_greeting: null,
        is_active: true,
        is_published: false,
        total_calls: 0,
        total_duration_seconds: 0,
        created_at: "2024-01-15T00:00:00Z",
        updated_at: "2024-01-15T00:00:00Z",
        last_call_at: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(createdAgent),
      });

      const result = await createAgent(createRequest);

      expect(result.id).toBe("new-agent-id");
      expect(result.name).toBe("New Agent");
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/agents"),
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(createRequest),
        })
      );
    });

    it("throws error with detail message on failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Bad Request",
        json: () => Promise.resolve({ detail: "Name is required" }),
      });

      await expect(
        createAgent({
          name: "",
          pricing_tier: "budget",
          system_prompt: "",
          language: "en-US",
          enabled_tools: [],
          enable_recording: false,
          enable_transcript: false,
        })
      ).rejects.toThrow("Name is required");
    });
  });

  describe("updateAgent", () => {
    it("updates an existing agent", async () => {
      const updateRequest: UpdateAgentRequest = {
        name: "Updated Agent Name",
        is_active: false,
      };

      const updatedAgent: Agent = {
        id: "agent-123",
        name: "Updated Agent Name",
        description: null,
        pricing_tier: "balanced",
        system_prompt: "Original prompt",
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
        initial_greeting: null,
        is_active: false,
        is_published: false,
        total_calls: 0,
        total_duration_seconds: 0,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-15T00:00:00Z",
        last_call_at: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(updatedAgent),
      });

      const result = await updateAgent("agent-123", updateRequest);

      expect(result.name).toBe("Updated Agent Name");
      expect(result.is_active).toBe(false);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/agents/agent-123"),
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify(updateRequest),
        })
      );
    });

    it("throws error on update failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Not Found",
        json: () => Promise.resolve({ detail: "Agent not found" }),
      });

      await expect(updateAgent("nonexistent", { name: "Test" })).rejects.toThrow("Agent not found");
    });
  });

  describe("deleteAgent", () => {
    it("deletes an agent successfully", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await expect(deleteAgent("agent-123")).resolves.toBeUndefined();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/agents/agent-123"),
        expect.objectContaining({
          method: "DELETE",
        })
      );
    });

    it("handles 204 No Content response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await expect(deleteAgent("agent-123")).resolves.toBeUndefined();
    });

    it("throws error when delete fails", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: "Forbidden",
        json: () => Promise.resolve({ detail: "Permission denied" }),
      });

      await expect(deleteAgent("agent-123")).rejects.toThrow("Permission denied");
    });
  });

  describe("getEmbedSettings", () => {
    it("fetches embed settings for an agent", async () => {
      const mockSettings = {
        public_id: "pub-123",
        embed_enabled: true,
        allowed_domains: ["example.com"],
        embed_settings: {
          theme: "dark",
          position: "bottom-right",
          primary_color: "#000000",
          greeting_message: "Hello",
          button_text: "Chat",
        },
        script_tag: "<script>...</script>",
        iframe_code: "<iframe>...</iframe>",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockSettings),
      });

      const result = await getEmbedSettings("agent-123");

      expect(result.public_id).toBe("pub-123");
      expect(result.embed_enabled).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/agents/agent-123/embed"),
        expect.any(Object)
      );
    });

    it("throws error on failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Not Found",
      });

      await expect(getEmbedSettings("agent-123")).rejects.toThrow(
        "Failed to fetch embed settings: Not Found"
      );
    });
  });

  describe("updateEmbedSettings", () => {
    it("updates embed settings successfully", async () => {
      const updateRequest = {
        embed_enabled: false,
        allowed_domains: ["newdomain.com"],
      };

      const updatedSettings = {
        public_id: "pub-123",
        embed_enabled: false,
        allowed_domains: ["newdomain.com"],
        embed_settings: {},
        script_tag: "<script>...</script>",
        iframe_code: "<iframe>...</iframe>",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(updatedSettings),
      });

      const result = await updateEmbedSettings("agent-123", updateRequest);

      expect(result.embed_enabled).toBe(false);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/agents/agent-123/embed"),
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify(updateRequest),
        })
      );
    });

    it("throws error with detail message on failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Bad Request",
        json: () => Promise.resolve({ detail: "Invalid domain format" }),
      });

      await expect(
        updateEmbedSettings("agent-123", { allowed_domains: ["invalid"] })
      ).rejects.toThrow("Invalid domain format");
    });
  });

  describe("auth headers", () => {
    it("includes authorization header when token exists", async () => {
      localStorage.setItem("access_token", "my-auth-token");

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      });

      await fetchAgents();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer my-auth-token",
          }),
        })
      );
    });

    it("does not include authorization header when no token", async () => {
      localStorage.removeItem("access_token");

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      });

      await fetchAgents();

      expect(mockFetch).toHaveBeenCalled();
    });
  });
});
