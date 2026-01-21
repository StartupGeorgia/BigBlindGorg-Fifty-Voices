import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";

// Unmock the module to test the real implementation
vi.unmock("@/hooks/use-auth");

// Import after unmocking
import { AuthProvider, useAuth } from "../use-auth";

// Mock next/navigation with proper vi.fn() that we can track
const mockPush = vi.fn();
const mockPathname = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => mockPathname(),
}));

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("useAuth", () => {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  );

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockPathname.mockReturnValue("/dashboard");
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("throws error when used outside AuthProvider", () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => {
      renderHook(() => useAuth());
    }).toThrow("useAuth must be used within an AuthProvider");

    consoleSpy.mockRestore();
  });

  it("starts with loading state when there is a stored token", async () => {
    localStorage.setItem("access_token", "test-token");
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ id: 1, email: "test@example.com", username: "testuser" }),
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it("starts with non-loading state when there is no stored token", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it("returns null user when not authenticated", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.user).toBeNull();
    });
  });

  it("fetches user when token exists on mount", async () => {
    localStorage.setItem("access_token", "existing-token");
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ id: 1, email: "test@example.com", username: "testuser" }),
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.user).toEqual({
        id: 1,
        email: "test@example.com",
        username: "testuser",
      });
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/me"),
      expect.objectContaining({
        headers: { Authorization: "Bearer existing-token" },
      })
    );
  });

  it("clears token when user fetch fails", async () => {
    localStorage.setItem("access_token", "invalid-token");
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.token).toBeNull();
      expect(localStorage.getItem("access_token")).toBeNull();
    });
  });

  describe("login", () => {
    it("logs in successfully with valid credentials", async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ access_token: "new-token" }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ id: 1, email: "user@test.com", username: "user" }),
        });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.login("user@test.com", "password123");
      });

      expect(localStorage.getItem("access_token")).toBe("new-token");
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });

    it("throws error on login failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: "Invalid credentials" }),
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      let error: Error | null = null;
      await act(async () => {
        try {
          await result.current.login("wrong@test.com", "wrongpassword");
        } catch (e) {
          error = e as Error;
        }
      });

      expect(error).not.toBeNull();
      expect(error?.message).toBe("Invalid credentials");
    });

    it("sends credentials in form-urlencoded format", async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ access_token: "new-token" }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ id: 1, email: "user@test.com", username: "user" }),
        });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.login("user@test.com", "password123");
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/auth/login"),
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        })
      );
    });
  });

  describe("register", () => {
    it("registers and auto-logs in on success", async () => {
      // Registration request
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 1 }),
      });
      // Login request (auto-login after registration)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ access_token: "new-token" }),
      });
      // Fetch user request
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 1, email: "new@test.com", username: "newuser" }),
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.register("new@test.com", "newuser", "password123");
      });

      // Should have made registration request
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/auth/register"),
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: "new@test.com", username: "newuser", password: "password123" }),
        })
      );
    });

    it("throws error on registration failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: "Email already exists" }),
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      let error: Error | null = null;
      await act(async () => {
        try {
          await result.current.register("existing@test.com", "user", "password");
        } catch (e) {
          error = e as Error;
        }
      });

      expect(error).not.toBeNull();
      expect(error?.message).toBe("Email already exists");
    });
  });

  describe("logout", () => {
    it("clears user state and redirects to login", async () => {
      localStorage.setItem("access_token", "test-token");
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 1, email: "test@example.com", username: "testuser" }),
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user).not.toBeNull();
      });

      act(() => {
        result.current.logout();
      });

      expect(result.current.user).toBeNull();
      expect(result.current.token).toBeNull();
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });

  describe("redirect logic", () => {
    it("redirects to login when not authenticated and on protected route", async () => {
      mockPathname.mockReturnValue("/dashboard");

      renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/login");
      });
    });

    it("does not redirect when on login page without auth", async () => {
      mockPathname.mockReturnValue("/login");

      renderHook(() => useAuth(), { wrapper });

      await waitFor(
        () => {
          // Give time for effect to run but expect no redirect
        },
        { timeout: 100 }
      ).catch(() => {
        // Timeout is expected, we're just waiting for effects to run
      });

      expect(mockPush).not.toHaveBeenCalled();
    });

    it("does not redirect when on register page without auth", async () => {
      mockPathname.mockReturnValue("/register");

      renderHook(() => useAuth(), { wrapper });

      await waitFor(
        () => {
          // Give time for effect to run but expect no redirect
        },
        { timeout: 100 }
      ).catch(() => {
        // Timeout is expected
      });

      expect(mockPush).not.toHaveBeenCalled();
    });

    it("does not redirect when on embed route without auth", async () => {
      mockPathname.mockReturnValue("/embed/agent-123");

      renderHook(() => useAuth(), { wrapper });

      await waitFor(
        () => {
          // Give time for effect to run but expect no redirect
        },
        { timeout: 100 }
      ).catch(() => {
        // Timeout is expected
      });

      expect(mockPush).not.toHaveBeenCalled();
    });

    it("redirects to dashboard when authenticated and on login page", async () => {
      mockPathname.mockReturnValue("/login");
      localStorage.setItem("access_token", "test-token");
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 1, email: "test@example.com", username: "testuser" }),
      });

      renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/dashboard");
      });
    });
  });

  describe("error handling", () => {
    it("handles network errors during login", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      let error: Error | null = null;
      await act(async () => {
        try {
          await result.current.login("user@test.com", "password");
        } catch (e) {
          error = e as Error;
        }
      });

      expect(error).not.toBeNull();
    });

    it("handles malformed JSON response during login", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error("Invalid JSON")),
      });

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      let error: Error | null = null;
      await act(async () => {
        try {
          await result.current.login("user@test.com", "password");
        } catch (e) {
          error = e as Error;
        }
      });

      expect(error).not.toBeNull();
      expect(error?.message).toBe("Login failed");
    });

    it("handles network errors during user fetch", async () => {
      localStorage.setItem("access_token", "test-token");
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.token).toBeNull();
        expect(localStorage.getItem("access_token")).toBeNull();
      });
    });
  });
});
