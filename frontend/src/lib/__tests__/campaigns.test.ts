import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  listCampaigns,
  getCampaign,
  createCampaign,
  updateCampaign,
  deleteCampaign,
  getCampaignContacts,
  addContactsToCampaign,
  removeContactFromCampaign,
  startCampaign,
  pauseCampaign,
  stopCampaign,
  restartCampaign,
  getCampaignStats,
  getDispositionStats,
  updateContactDisposition,
  getDispositionOptions,
  previewContactsByFilter,
  addContactsByFilter,
  type Campaign,
  type CampaignContact,
  type CampaignStats,
  type CreateCampaignRequest,
} from "../api/campaigns";

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("Campaigns API", () => {
  let api: { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn>; put: ReturnType<typeof vi.fn>; delete: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    vi.clearAllMocks();
    const module = await import("@/lib/api");
    api = module.api as typeof api;
  });

  const mockCampaign: Campaign = {
    id: "campaign-123",
    workspace_id: "ws-123",
    agent_id: "agent-456",
    agent_name: "Sales Agent",
    name: "Test Campaign",
    description: "A test outbound campaign",
    status: "draft",
    from_phone_number: "+15551234567",
    scheduled_start: "2024-01-20T09:00:00Z",
    scheduled_end: "2024-01-25T17:00:00Z",
    calling_hours_start: "09:00",
    calling_hours_end: "17:00",
    calling_days: [0, 1, 2, 3, 4],
    timezone: "America/New_York",
    calls_per_minute: 5,
    max_concurrent_calls: 10,
    max_attempts_per_contact: 3,
    retry_delay_minutes: 60,
    total_contacts: 100,
    contacts_called: 0,
    contacts_completed: 0,
    contacts_failed: 0,
    total_call_duration_seconds: 0,
    last_error: null,
    error_count: 0,
    last_error_at: null,
    started_at: null,
    completed_at: null,
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
  };

  describe("listCampaigns", () => {
    it("fetches all campaigns", async () => {
      api.get.mockResolvedValueOnce({ data: [mockCampaign] });

      const result = await listCampaigns();

      expect(result).toHaveLength(1);
      expect(result[0].id).toBe("campaign-123");
      expect(api.get).toHaveBeenCalledWith("/api/v1/campaigns");
    });

    it("fetches campaigns filtered by workspace_id", async () => {
      api.get.mockResolvedValueOnce({ data: [mockCampaign] });

      await listCampaigns({ workspace_id: "ws-123" });

      expect(api.get).toHaveBeenCalledWith("/api/v1/campaigns?workspace_id=ws-123");
    });

    it("fetches campaigns filtered by status", async () => {
      api.get.mockResolvedValueOnce({ data: [] });

      await listCampaigns({ status: "running" });

      expect(api.get).toHaveBeenCalledWith("/api/v1/campaigns?status=running");
    });

    it("combines multiple filter parameters", async () => {
      api.get.mockResolvedValueOnce({ data: [] });

      await listCampaigns({ workspace_id: "ws-123", status: "completed" });

      expect(api.get).toHaveBeenCalledWith(
        "/api/v1/campaigns?workspace_id=ws-123&status=completed"
      );
    });
  });

  describe("getCampaign", () => {
    it("fetches a specific campaign", async () => {
      api.get.mockResolvedValueOnce({ data: mockCampaign });

      const result = await getCampaign("campaign-123");

      expect(result.id).toBe("campaign-123");
      expect(result.name).toBe("Test Campaign");
      expect(api.get).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123");
    });
  });

  describe("createCampaign", () => {
    it("creates a new campaign", async () => {
      const createRequest: CreateCampaignRequest = {
        workspace_id: "ws-123",
        agent_id: "agent-456",
        name: "New Campaign",
        description: "Campaign description",
        from_phone_number: "+15551234567",
        calling_hours_start: "09:00",
        calling_hours_end: "17:00",
        calling_days: [0, 1, 2, 3, 4],
        timezone: "America/New_York",
        calls_per_minute: 5,
        max_concurrent_calls: 10,
        contact_ids: [1, 2, 3],
      };

      api.post.mockResolvedValueOnce({ data: { ...mockCampaign, name: "New Campaign" } });

      const result = await createCampaign(createRequest);

      expect(result.name).toBe("New Campaign");
      expect(api.post).toHaveBeenCalledWith("/api/v1/campaigns", createRequest);
    });
  });

  describe("updateCampaign", () => {
    it("updates an existing campaign", async () => {
      const updateRequest = {
        name: "Updated Campaign Name",
        calls_per_minute: 10,
      };

      api.put.mockResolvedValueOnce({
        data: { ...mockCampaign, ...updateRequest },
      });

      const result = await updateCampaign("campaign-123", updateRequest);

      expect(result.name).toBe("Updated Campaign Name");
      expect(result.calls_per_minute).toBe(10);
      expect(api.put).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123", updateRequest);
    });
  });

  describe("deleteCampaign", () => {
    it("deletes a campaign", async () => {
      api.delete.mockResolvedValueOnce({});

      await deleteCampaign("campaign-123");

      expect(api.delete).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123");
    });
  });

  describe("getCampaignContacts", () => {
    const mockContact: CampaignContact = {
      id: "cc-123",
      contact_id: 1,
      status: "pending",
      attempts: 0,
      last_attempt_at: null,
      next_attempt_at: null,
      last_call_duration_seconds: 0,
      last_call_outcome: null,
      priority: 1,
      disposition: null,
      disposition_notes: null,
      callback_requested_at: null,
      contact_name: "John Doe",
      contact_phone: "+15559876543",
    };

    it("fetches campaign contacts", async () => {
      api.get.mockResolvedValueOnce({ data: [mockContact] });

      const result = await getCampaignContacts("campaign-123");

      expect(result).toHaveLength(1);
      expect(result[0].contact_name).toBe("John Doe");
      expect(api.get).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123/contacts");
    });

    it("fetches campaign contacts with filters", async () => {
      api.get.mockResolvedValueOnce({ data: [] });

      await getCampaignContacts("campaign-123", {
        status: "completed",
        limit: 50,
        offset: 10,
      });

      expect(api.get).toHaveBeenCalledWith(
        "/api/v1/campaigns/campaign-123/contacts?status=completed&limit=50&offset=10"
      );
    });
  });

  describe("addContactsToCampaign", () => {
    it("adds contacts to a campaign", async () => {
      api.post.mockResolvedValueOnce({ data: { added: 5 } });

      const result = await addContactsToCampaign("campaign-123", [1, 2, 3, 4, 5]);

      expect(result.added).toBe(5);
      expect(api.post).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123/contacts", {
        contact_ids: [1, 2, 3, 4, 5],
      });
    });
  });

  describe("removeContactFromCampaign", () => {
    it("removes a contact from a campaign", async () => {
      api.delete.mockResolvedValueOnce({});

      await removeContactFromCampaign("campaign-123", 1);

      expect(api.delete).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123/contacts/1");
    });
  });

  describe("Campaign Status Operations", () => {
    describe("startCampaign", () => {
      it("starts a campaign", async () => {
        api.post.mockResolvedValueOnce({
          data: { ...mockCampaign, status: "running" },
        });

        const result = await startCampaign("campaign-123");

        expect(result.status).toBe("running");
        expect(api.post).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123/start");
      });
    });

    describe("pauseCampaign", () => {
      it("pauses a running campaign", async () => {
        api.post.mockResolvedValueOnce({
          data: { ...mockCampaign, status: "paused" },
        });

        const result = await pauseCampaign("campaign-123");

        expect(result.status).toBe("paused");
        expect(api.post).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123/pause");
      });
    });

    describe("stopCampaign", () => {
      it("stops a campaign", async () => {
        api.post.mockResolvedValueOnce({
          data: { ...mockCampaign, status: "canceled" },
        });

        const result = await stopCampaign("campaign-123");

        expect(result.status).toBe("canceled");
        expect(api.post).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123/stop");
      });
    });

    describe("restartCampaign", () => {
      it("restarts a completed campaign", async () => {
        api.post.mockResolvedValueOnce({
          data: { ...mockCampaign, status: "running" },
        });

        const result = await restartCampaign("campaign-123");

        expect(result.status).toBe("running");
        expect(api.post).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123/restart");
      });
    });
  });

  describe("getCampaignStats", () => {
    it("fetches campaign statistics", async () => {
      const mockStats: CampaignStats = {
        total_contacts: 100,
        contacts_pending: 50,
        contacts_calling: 5,
        contacts_completed: 35,
        contacts_failed: 5,
        contacts_no_answer: 3,
        contacts_busy: 2,
        contacts_skipped: 0,
        total_calls_made: 50,
        total_call_duration_seconds: 9000,
        average_call_duration_seconds: 180,
        completion_rate: 0.35,
      };

      api.get.mockResolvedValueOnce({ data: mockStats });

      const result = await getCampaignStats("campaign-123");

      expect(result.total_contacts).toBe(100);
      expect(result.contacts_completed).toBe(35);
      expect(result.completion_rate).toBe(0.35);
      expect(api.get).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123/stats");
    });
  });

  describe("Disposition Operations", () => {
    describe("getDispositionStats", () => {
      it("fetches disposition statistics", async () => {
        const mockStats = {
          total: 50,
          by_disposition: {
            interested: 20,
            not_interested: 15,
            callback_requested: 10,
            wrong_number: 5,
          },
          callbacks_pending: 10,
        };

        api.get.mockResolvedValueOnce({ data: mockStats });

        const result = await getDispositionStats("campaign-123");

        expect(result.total).toBe(50);
        expect(result.by_disposition.interested).toBe(20);
        expect(result.callbacks_pending).toBe(10);
        expect(api.get).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123/dispositions");
      });
    });

    describe("updateContactDisposition", () => {
      it("updates contact disposition", async () => {
        const mockContact: CampaignContact = {
          id: "cc-123",
          contact_id: 1,
          status: "completed",
          attempts: 1,
          last_attempt_at: "2024-01-15T10:00:00Z",
          next_attempt_at: null,
          last_call_duration_seconds: 120,
          last_call_outcome: "answered",
          priority: 1,
          disposition: "interested",
          disposition_notes: "Will call back next week",
          callback_requested_at: "2024-01-22T10:00:00Z",
          contact_name: "John Doe",
          contact_phone: "+15559876543",
        };

        api.put.mockResolvedValueOnce({ data: mockContact });

        const result = await updateContactDisposition("campaign-123", 1, {
          disposition: "interested",
          disposition_notes: "Will call back next week",
          callback_requested_at: "2024-01-22T10:00:00Z",
        });

        expect(result.disposition).toBe("interested");
        expect(api.put).toHaveBeenCalledWith(
          "/api/v1/campaigns/campaign-123/contacts/1/disposition",
          {
            disposition: "interested",
            disposition_notes: "Will call back next week",
            callback_requested_at: "2024-01-22T10:00:00Z",
          }
        );
      });
    });

    describe("getDispositionOptions", () => {
      it("fetches available disposition options", async () => {
        const mockOptions = {
          positive: [
            { value: "interested", label: "Interested" },
            { value: "scheduled", label: "Meeting Scheduled" },
          ],
          neutral: [{ value: "callback", label: "Callback Requested" }],
          negative: [
            { value: "not_interested", label: "Not Interested" },
            { value: "do_not_call", label: "Do Not Call" },
          ],
          technical: [
            { value: "wrong_number", label: "Wrong Number" },
            { value: "no_answer", label: "No Answer" },
          ],
        };

        api.get.mockResolvedValueOnce({ data: mockOptions });

        const result = await getDispositionOptions();

        expect(result.positive).toHaveLength(2);
        expect(result.negative).toHaveLength(2);
        expect(api.get).toHaveBeenCalledWith("/api/v1/campaigns/dispositions/options");
      });
    });
  });

  describe("Contact Filter Operations", () => {
    describe("previewContactsByFilter", () => {
      it("previews contacts matching filter", async () => {
        const mockPreview = {
          total_matching: 50,
          already_in_campaign: 10,
          will_be_added: 40,
        };

        api.post.mockResolvedValueOnce({ data: mockPreview });

        const result = await previewContactsByFilter("campaign-123", {
          status: ["active"],
          tags: ["vip"],
          exclude_existing: true,
        });

        expect(result.total_matching).toBe(50);
        expect(result.will_be_added).toBe(40);
        expect(api.post).toHaveBeenCalledWith(
          "/api/v1/campaigns/campaign-123/contacts/filter/preview",
          {
            status: ["active"],
            tags: ["vip"],
            exclude_existing: true,
          }
        );
      });
    });

    describe("addContactsByFilter", () => {
      it("adds contacts by filter criteria", async () => {
        const mockResult = {
          added: 40,
          total_matching: 50,
        };

        api.post.mockResolvedValueOnce({ data: mockResult });

        const result = await addContactsByFilter("campaign-123", {
          status: ["active"],
          tags: ["vip"],
        });

        expect(result.added).toBe(40);
        expect(api.post).toHaveBeenCalledWith("/api/v1/campaigns/campaign-123/contacts/filter", {
          status: ["active"],
          tags: ["vip"],
        });
      });
    });
  });
});
