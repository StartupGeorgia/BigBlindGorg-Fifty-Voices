import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  listCalls,
  getCall,
  getAgentCallStats,
  type CallRecord,
  type CallRecordListResponse,
  type CallStats,
  type ListCallsParams,
} from "../api/calls";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("Calls API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    localStorage.setItem("access_token", "test-token");
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("listCalls", () => {
    const mockCallRecord: CallRecord = {
      id: "call-123",
      provider: "telnyx",
      provider_call_id: "telnyx-call-456",
      agent_id: "agent-789",
      agent_name: "Test Agent",
      contact_id: 1,
      contact_name: "John Doe",
      workspace_id: "ws-123",
      workspace_name: "Main Workspace",
      direction: "outbound",
      status: "completed",
      from_number: "+15551234567",
      to_number: "+15559876543",
      duration_seconds: 120,
      recording_url: "https://example.com/recording.mp3",
      transcript: "Hello, this is a test call...",
      started_at: "2024-01-15T10:00:00Z",
      answered_at: "2024-01-15T10:00:05Z",
      ended_at: "2024-01-15T10:02:00Z",
    };

    it("fetches calls with default parameters", async () => {
      const mockResponse: CallRecordListResponse = {
        calls: [mockCallRecord],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await listCalls();

      expect(result.calls).toHaveLength(1);
      expect(result.total).toBe(1);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/calls"),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer test-token",
          }),
        })
      );
    });

    it("fetches calls with pagination parameters", async () => {
      const mockResponse: CallRecordListResponse = {
        calls: [],
        total: 50,
        page: 2,
        page_size: 10,
        total_pages: 5,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const params: ListCallsParams = {
        page: 2,
        page_size: 10,
      };

      await listCalls(params);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/page=2/),
        expect.any(Object)
      );
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/page_size=10/),
        expect.any(Object)
      );
    });

    it("fetches calls filtered by agent_id", async () => {
      const mockResponse: CallRecordListResponse = {
        calls: [mockCallRecord],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await listCalls({ agent_id: "agent-789" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/agent_id=agent-789/),
        expect.any(Object)
      );
    });

    it("fetches calls filtered by workspace_id", async () => {
      const mockResponse: CallRecordListResponse = {
        calls: [mockCallRecord],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await listCalls({ workspace_id: "ws-123" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/workspace_id=ws-123/),
        expect.any(Object)
      );
    });

    it("fetches calls filtered by direction", async () => {
      const mockResponse: CallRecordListResponse = {
        calls: [mockCallRecord],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await listCalls({ direction: "inbound" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/direction=inbound/),
        expect.any(Object)
      );
    });

    it("fetches calls filtered by status", async () => {
      const mockResponse: CallRecordListResponse = {
        calls: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await listCalls({ status: "failed" });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringMatching(/status=failed/),
        expect.any(Object)
      );
    });

    it("combines multiple filter parameters", async () => {
      const mockResponse: CallRecordListResponse = {
        calls: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await listCalls({
        page: 1,
        page_size: 10,
        agent_id: "agent-123",
        direction: "outbound",
        status: "completed",
      });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain("page=1");
      expect(calledUrl).toContain("page_size=10");
      expect(calledUrl).toContain("agent_id=agent-123");
      expect(calledUrl).toContain("direction=outbound");
      expect(calledUrl).toContain("status=completed");
    });

    it("throws error on failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Internal Server Error",
        json: () => Promise.resolve({ detail: "Database error" }),
      });

      await expect(listCalls()).rejects.toThrow("Database error");
    });

    it("handles empty response", async () => {
      const mockResponse: CallRecordListResponse = {
        calls: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await listCalls();

      expect(result.calls).toHaveLength(0);
      expect(result.total).toBe(0);
    });
  });

  describe("getCall", () => {
    it("fetches a specific call by ID", async () => {
      const mockCallRecord: CallRecord = {
        id: "call-123",
        provider: "telnyx",
        provider_call_id: "telnyx-call-456",
        agent_id: "agent-789",
        agent_name: "Test Agent",
        contact_id: 1,
        contact_name: "John Doe",
        workspace_id: "ws-123",
        workspace_name: "Main Workspace",
        direction: "inbound",
        status: "completed",
        from_number: "+15559876543",
        to_number: "+15551234567",
        duration_seconds: 300,
        recording_url: "https://example.com/recording.mp3",
        transcript: "This is the call transcript...",
        started_at: "2024-01-15T10:00:00Z",
        answered_at: "2024-01-15T10:00:02Z",
        ended_at: "2024-01-15T10:05:00Z",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCallRecord),
      });

      const result = await getCall("call-123");

      expect(result.id).toBe("call-123");
      expect(result.direction).toBe("inbound");
      expect(result.duration_seconds).toBe(300);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/calls/call-123"),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer test-token",
          }),
        })
      );
    });

    it("throws error when call not found", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Not Found",
        json: () => Promise.resolve({ detail: "Call not found" }),
      });

      await expect(getCall("nonexistent")).rejects.toThrow("Call not found");
    });

    it("handles call with null optional fields", async () => {
      const mockCallRecord: CallRecord = {
        id: "call-456",
        provider: "twilio",
        provider_call_id: "twilio-call-789",
        agent_id: null,
        agent_name: null,
        contact_id: null,
        contact_name: null,
        workspace_id: null,
        workspace_name: null,
        direction: "outbound",
        status: "failed",
        from_number: "+15551234567",
        to_number: "+15559876543",
        duration_seconds: 0,
        recording_url: null,
        transcript: null,
        started_at: "2024-01-15T10:00:00Z",
        answered_at: null,
        ended_at: "2024-01-15T10:00:30Z",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCallRecord),
      });

      const result = await getCall("call-456");

      expect(result.agent_id).toBeNull();
      expect(result.recording_url).toBeNull();
      expect(result.answered_at).toBeNull();
    });
  });

  describe("getAgentCallStats", () => {
    it("fetches call statistics for an agent", async () => {
      const mockStats: CallStats = {
        total_calls: 100,
        completed_calls: 85,
        inbound_calls: 40,
        outbound_calls: 60,
        total_duration_seconds: 36000,
        average_duration_seconds: 360,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockStats),
      });

      const result = await getAgentCallStats("agent-123");

      expect(result.total_calls).toBe(100);
      expect(result.completed_calls).toBe(85);
      expect(result.inbound_calls).toBe(40);
      expect(result.outbound_calls).toBe(60);
      expect(result.total_duration_seconds).toBe(36000);
      expect(result.average_duration_seconds).toBe(360);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/calls/agent/agent-123/stats"),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer test-token",
          }),
        })
      );
    });

    it("throws error when agent not found", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Not Found",
        json: () => Promise.resolve({ detail: "Agent not found" }),
      });

      await expect(getAgentCallStats("nonexistent")).rejects.toThrow("Agent not found");
    });

    it("handles stats for agent with no calls", async () => {
      const mockStats: CallStats = {
        total_calls: 0,
        completed_calls: 0,
        inbound_calls: 0,
        outbound_calls: 0,
        total_duration_seconds: 0,
        average_duration_seconds: 0,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockStats),
      });

      const result = await getAgentCallStats("new-agent");

      expect(result.total_calls).toBe(0);
      expect(result.average_duration_seconds).toBe(0);
    });
  });

  describe("auth headers", () => {
    it("includes authorization header when token exists", async () => {
      localStorage.setItem("access_token", "my-auth-token");

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            calls: [],
            total: 0,
            page: 1,
            page_size: 20,
            total_pages: 0,
          }),
      });

      await listCalls();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer my-auth-token",
          }),
        })
      );
    });

    it("handles missing token gracefully", async () => {
      localStorage.removeItem("access_token");

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            calls: [],
            total: 0,
            page: 1,
            page_size: 20,
            total_pages: 0,
          }),
      });

      await listCalls();

      expect(mockFetch).toHaveBeenCalled();
    });
  });

  describe("error handling", () => {
    it("throws error with fallback message when no detail provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Service Unavailable",
        json: () => Promise.reject(new Error("Invalid JSON")),
      });

      await expect(listCalls()).rejects.toThrow("Service Unavailable");
    });
  });
});
