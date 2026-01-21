import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchComplianceStatus,
  fetchPrivacySettings,
  updatePrivacySettings,
  recordConsent,
  exportUserData,
  ccpaOptOut,
  ccpaOptIn,
  withdrawConsent,
  deleteUserData,
  type ComplianceOverview,
  type PrivacySettings,
  type DataExport,
} from "../api/compliance";

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("Compliance API", () => {
  let api: { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn>; patch: ReturnType<typeof vi.fn>; delete: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    vi.clearAllMocks();
    const module = await import("@/lib/api");
    api = module.api as typeof api;
  });

  describe("fetchComplianceStatus", () => {
    it("fetches compliance status overview", async () => {
      const mockStatus: ComplianceOverview = {
        gdpr: {
          completed: 8,
          total: 10,
          percentage: 80,
          checks: [
            {
              id: "privacy_policy",
              label: "Privacy Policy",
              description: "Define your privacy policy URL",
              status: "complete",
              action_url: "/settings",
              action_label: "Set Privacy Policy",
            },
            {
              id: "data_processing_consent",
              label: "Data Processing Consent",
              description: "Record user consent for data processing",
              status: "incomplete",
              action_label: "Record Consent",
            },
          ],
        },
        ccpa: {
          completed: 10,
          total: 10,
          percentage: 100,
          checks: [
            {
              id: "opt_out_mechanism",
              label: "Opt-Out Mechanism",
              description: "CCPA opt-out of data sharing",
              status: "complete",
            },
          ],
        },
      };

      api.get.mockResolvedValueOnce({ data: mockStatus });

      const result = await fetchComplianceStatus();

      expect(result.gdpr.percentage).toBe(80);
      expect(result.ccpa.percentage).toBe(100);
      expect(result.gdpr.checks).toHaveLength(2);
      expect(api.get).toHaveBeenCalledWith("/api/v1/compliance/status");
    });
  });

  describe("fetchPrivacySettings", () => {
    it("fetches user privacy settings", async () => {
      const mockSettings: PrivacySettings = {
        privacy_policy_url: "https://example.com/privacy",
        privacy_policy_accepted_at: "2024-01-01T00:00:00Z",
        data_retention_days: 365,
        openai_dpa_signed: true,
        openai_dpa_signed_at: "2024-01-01T00:00:00Z",
        telnyx_dpa_signed: true,
        telnyx_dpa_signed_at: "2024-01-01T00:00:00Z",
        deepgram_dpa_signed: false,
        deepgram_dpa_signed_at: null,
        elevenlabs_dpa_signed: false,
        elevenlabs_dpa_signed_at: null,
        ccpa_opt_out: false,
        ccpa_opt_out_at: null,
        last_data_export_at: "2024-01-10T12:00:00Z",
      };

      api.get.mockResolvedValueOnce({ data: mockSettings });

      const result = await fetchPrivacySettings();

      expect(result.privacy_policy_url).toBe("https://example.com/privacy");
      expect(result.data_retention_days).toBe(365);
      expect(result.openai_dpa_signed).toBe(true);
      expect(result.ccpa_opt_out).toBe(false);
      expect(api.get).toHaveBeenCalledWith("/api/v1/compliance/privacy-settings");
    });

    it("handles null values for optional fields", async () => {
      const mockSettings: PrivacySettings = {
        privacy_policy_url: null,
        privacy_policy_accepted_at: null,
        data_retention_days: 30,
        openai_dpa_signed: false,
        openai_dpa_signed_at: null,
        telnyx_dpa_signed: false,
        telnyx_dpa_signed_at: null,
        deepgram_dpa_signed: false,
        deepgram_dpa_signed_at: null,
        elevenlabs_dpa_signed: false,
        elevenlabs_dpa_signed_at: null,
        ccpa_opt_out: false,
        ccpa_opt_out_at: null,
        last_data_export_at: null,
      };

      api.get.mockResolvedValueOnce({ data: mockSettings });

      const result = await fetchPrivacySettings();

      expect(result.privacy_policy_url).toBeNull();
      expect(result.last_data_export_at).toBeNull();
    });
  });

  describe("updatePrivacySettings", () => {
    it("updates privacy settings", async () => {
      const updateRequest = {
        privacy_policy_url: "https://newsite.com/privacy",
        data_retention_days: 180,
      };

      const mockResponse: PrivacySettings = {
        privacy_policy_url: "https://newsite.com/privacy",
        privacy_policy_accepted_at: null,
        data_retention_days: 180,
        openai_dpa_signed: false,
        openai_dpa_signed_at: null,
        telnyx_dpa_signed: false,
        telnyx_dpa_signed_at: null,
        deepgram_dpa_signed: false,
        deepgram_dpa_signed_at: null,
        elevenlabs_dpa_signed: false,
        elevenlabs_dpa_signed_at: null,
        ccpa_opt_out: false,
        ccpa_opt_out_at: null,
        last_data_export_at: null,
      };

      api.patch.mockResolvedValueOnce({ data: mockResponse });

      const result = await updatePrivacySettings(updateRequest);

      expect(result.privacy_policy_url).toBe("https://newsite.com/privacy");
      expect(result.data_retention_days).toBe(180);
      expect(api.patch).toHaveBeenCalledWith("/api/v1/compliance/privacy-settings", updateRequest);
    });

    it("updates DPA signed status", async () => {
      const updateRequest = {
        openai_dpa_signed: true,
        telnyx_dpa_signed: true,
      };

      api.patch.mockResolvedValueOnce({
        data: {
          ...{
            privacy_policy_url: null,
            privacy_policy_accepted_at: null,
            data_retention_days: 30,
            deepgram_dpa_signed: false,
            deepgram_dpa_signed_at: null,
            elevenlabs_dpa_signed: false,
            elevenlabs_dpa_signed_at: null,
            ccpa_opt_out: false,
            ccpa_opt_out_at: null,
            last_data_export_at: null,
          },
          openai_dpa_signed: true,
          openai_dpa_signed_at: "2024-01-15T10:00:00Z",
          telnyx_dpa_signed: true,
          telnyx_dpa_signed_at: "2024-01-15T10:00:00Z",
        },
      });

      const result = await updatePrivacySettings(updateRequest);

      expect(result.openai_dpa_signed).toBe(true);
      expect(result.telnyx_dpa_signed).toBe(true);
    });
  });

  describe("recordConsent", () => {
    it("records user consent", async () => {
      api.post.mockResolvedValueOnce({ data: { message: "Consent recorded successfully" } });

      const result = await recordConsent("data_processing", true);

      expect(result.message).toBe("Consent recorded successfully");
      expect(api.post).toHaveBeenCalledWith("/api/v1/compliance/consent", {
        consent_type: "data_processing",
        granted: true,
      });
    });

    it("records call recording consent", async () => {
      api.post.mockResolvedValueOnce({ data: { message: "Consent recorded" } });

      await recordConsent("call_recording", true);

      expect(api.post).toHaveBeenCalledWith("/api/v1/compliance/consent", {
        consent_type: "call_recording",
        granted: true,
      });
    });

    it("records consent denial", async () => {
      api.post.mockResolvedValueOnce({ data: { message: "Consent recorded" } });

      await recordConsent("marketing", false);

      expect(api.post).toHaveBeenCalledWith("/api/v1/compliance/consent", {
        consent_type: "marketing",
        granted: false,
      });
    });
  });

  describe("exportUserData", () => {
    it("exports all user data", async () => {
      const mockExport: DataExport = {
        user: { id: 1, email: "user@example.com", username: "testuser" },
        settings: { theme: "dark", notifications: true },
        privacy_settings: { data_retention_days: 365 },
        agents: [{ id: "agent-1", name: "Agent 1" }],
        workspaces: [{ id: "ws-1", name: "Workspace 1" }],
        contacts: [{ id: 1, name: "Contact 1", phone: "+15551234567" }],
        appointments: [{ id: "apt-1", title: "Meeting" }],
        call_records: [{ id: "call-1", duration_seconds: 120 }],
        call_interactions: [{ id: "int-1", type: "tool_call" }],
        consent_records: [{ id: "consent-1", type: "data_processing", granted: true }],
        exported_at: "2024-01-15T12:00:00Z",
      };

      api.get.mockResolvedValueOnce({ data: mockExport });

      const result = await exportUserData();

      expect(result.user.email).toBe("user@example.com");
      expect(result.agents).toHaveLength(1);
      expect(result.exported_at).toBe("2024-01-15T12:00:00Z");
      expect(api.get).toHaveBeenCalledWith("/api/v1/compliance/export");
    });

    it("handles empty data export", async () => {
      const mockExport: DataExport = {
        user: { id: 1, email: "newuser@example.com", username: "newuser" },
        settings: null,
        privacy_settings: null,
        agents: [],
        workspaces: [],
        contacts: [],
        appointments: [],
        call_records: [],
        call_interactions: [],
        consent_records: [],
        exported_at: "2024-01-15T12:00:00Z",
      };

      api.get.mockResolvedValueOnce({ data: mockExport });

      const result = await exportUserData();

      expect(result.agents).toHaveLength(0);
      expect(result.settings).toBeNull();
    });
  });

  describe("ccpaOptOut", () => {
    it("opts out of data sharing", async () => {
      api.post.mockResolvedValueOnce({
        data: { message: "Successfully opted out of data sharing" },
      });

      const result = await ccpaOptOut();

      expect(result.message).toBe("Successfully opted out of data sharing");
      expect(api.post).toHaveBeenCalledWith("/api/v1/compliance/ccpa/opt-out");
    });
  });

  describe("ccpaOptIn", () => {
    it("opts back in to data sharing", async () => {
      api.post.mockResolvedValueOnce({
        data: { message: "Successfully opted back in to data sharing" },
      });

      const result = await ccpaOptIn();

      expect(result.message).toBe("Successfully opted back in to data sharing");
      expect(api.post).toHaveBeenCalledWith("/api/v1/compliance/ccpa/opt-in");
    });
  });

  describe("withdrawConsent", () => {
    it("withdraws data processing consent", async () => {
      api.post.mockResolvedValueOnce({
        data: { message: "Consent withdrawn successfully" },
      });

      const result = await withdrawConsent("data_processing");

      expect(result.message).toBe("Consent withdrawn successfully");
      expect(api.post).toHaveBeenCalledWith("/api/v1/compliance/consent/withdraw", {
        consent_type: "data_processing",
        granted: false,
      });
    });

    it("withdraws call recording consent", async () => {
      api.post.mockResolvedValueOnce({
        data: { message: "Consent withdrawn" },
      });

      await withdrawConsent("call_recording");

      expect(api.post).toHaveBeenCalledWith("/api/v1/compliance/consent/withdraw", {
        consent_type: "call_recording",
        granted: false,
      });
    });
  });

  describe("deleteUserData", () => {
    it("deletes all user data", async () => {
      const mockResponse = {
        deleted_counts: {
          agents: 5,
          workspaces: 2,
          contacts: 100,
          appointments: 25,
          call_records: 150,
          settings: 1,
        },
        deleted_at: "2024-01-15T12:00:00Z",
      };

      api.delete.mockResolvedValueOnce({ data: mockResponse });

      const result = await deleteUserData();

      expect(result.deleted_counts.agents).toBe(5);
      expect(result.deleted_counts.contacts).toBe(100);
      expect(result.deleted_at).toBe("2024-01-15T12:00:00Z");
      expect(api.delete).toHaveBeenCalledWith("/api/v1/compliance/data");
    });

    it("handles deletion with zero counts", async () => {
      const mockResponse = {
        deleted_counts: {
          agents: 0,
          workspaces: 0,
          contacts: 0,
          appointments: 0,
          call_records: 0,
          settings: 0,
        },
        deleted_at: "2024-01-15T12:00:00Z",
      };

      api.delete.mockResolvedValueOnce({ data: mockResponse });

      const result = await deleteUserData();

      expect(result.deleted_counts.agents).toBe(0);
    });
  });
});
