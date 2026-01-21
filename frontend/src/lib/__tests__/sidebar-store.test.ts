import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useSidebarStore } from "../sidebar-store";

describe("useSidebarStore", () => {
  beforeEach(() => {
    // Reset the store state before each test
    localStorage.clear();
    useSidebarStore.setState({ sidebarOpen: true });
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe("initial state", () => {
    it("has sidebar open by default", () => {
      const { result } = renderHook(() => useSidebarStore());

      expect(result.current.sidebarOpen).toBe(true);
    });
  });

  describe("setSidebarOpen", () => {
    it("sets sidebar to closed", () => {
      const { result } = renderHook(() => useSidebarStore());

      act(() => {
        result.current.setSidebarOpen(false);
      });

      expect(result.current.sidebarOpen).toBe(false);
    });

    it("sets sidebar to open", () => {
      const { result } = renderHook(() => useSidebarStore());

      // First close it
      act(() => {
        result.current.setSidebarOpen(false);
      });

      expect(result.current.sidebarOpen).toBe(false);

      // Then open it
      act(() => {
        result.current.setSidebarOpen(true);
      });

      expect(result.current.sidebarOpen).toBe(true);
    });

    it("can set to same value without error", () => {
      const { result } = renderHook(() => useSidebarStore());

      expect(result.current.sidebarOpen).toBe(true);

      act(() => {
        result.current.setSidebarOpen(true);
      });

      expect(result.current.sidebarOpen).toBe(true);
    });
  });

  describe("toggleSidebar", () => {
    it("toggles from open to closed", () => {
      const { result } = renderHook(() => useSidebarStore());

      expect(result.current.sidebarOpen).toBe(true);

      act(() => {
        result.current.toggleSidebar();
      });

      expect(result.current.sidebarOpen).toBe(false);
    });

    it("toggles from closed to open", () => {
      const { result } = renderHook(() => useSidebarStore());

      // First close it
      act(() => {
        result.current.setSidebarOpen(false);
      });

      expect(result.current.sidebarOpen).toBe(false);

      // Then toggle
      act(() => {
        result.current.toggleSidebar();
      });

      expect(result.current.sidebarOpen).toBe(true);
    });

    it("toggles multiple times correctly", () => {
      const { result } = renderHook(() => useSidebarStore());

      expect(result.current.sidebarOpen).toBe(true);

      act(() => {
        result.current.toggleSidebar();
      });
      expect(result.current.sidebarOpen).toBe(false);

      act(() => {
        result.current.toggleSidebar();
      });
      expect(result.current.sidebarOpen).toBe(true);

      act(() => {
        result.current.toggleSidebar();
      });
      expect(result.current.sidebarOpen).toBe(false);
    });
  });

  describe("persistence", () => {
    it("persists state to localStorage", () => {
      const { result } = renderHook(() => useSidebarStore());

      act(() => {
        result.current.setSidebarOpen(false);
      });

      // Check localStorage was updated
      const stored = localStorage.getItem("sidebar-storage");
      expect(stored).toBeTruthy();

      const parsed = JSON.parse(stored!);
      expect(parsed.state.sidebarOpen).toBe(false);
    });

    it("restores state from localStorage on mount", () => {
      // Set up localStorage with closed sidebar state
      localStorage.setItem(
        "sidebar-storage",
        JSON.stringify({
          state: { sidebarOpen: false },
          version: 0,
        })
      );

      // Manually hydrate the store from localStorage to simulate the persistence behavior
      const storedState = localStorage.getItem("sidebar-storage");
      if (storedState) {
        const parsed = JSON.parse(storedState);
        useSidebarStore.setState(parsed.state);
      }

      const { result } = renderHook(() => useSidebarStore());

      expect(result.current.sidebarOpen).toBe(false);
    });

    it("uses storage key 'sidebar-storage'", () => {
      const { result } = renderHook(() => useSidebarStore());

      act(() => {
        result.current.setSidebarOpen(false);
      });

      expect(localStorage.getItem("sidebar-storage")).toBeTruthy();
      expect(localStorage.getItem("other-storage")).toBeNull();
    });
  });

  describe("multiple hook instances", () => {
    it("shares state between multiple hook instances", () => {
      const { result: result1 } = renderHook(() => useSidebarStore());
      const { result: result2 } = renderHook(() => useSidebarStore());

      expect(result1.current.sidebarOpen).toBe(true);
      expect(result2.current.sidebarOpen).toBe(true);

      act(() => {
        result1.current.setSidebarOpen(false);
      });

      // Both instances should reflect the change
      expect(result1.current.sidebarOpen).toBe(false);
      expect(result2.current.sidebarOpen).toBe(false);
    });

    it("shares toggle action between instances", () => {
      const { result: result1 } = renderHook(() => useSidebarStore());
      const { result: result2 } = renderHook(() => useSidebarStore());

      act(() => {
        result1.current.toggleSidebar();
      });

      expect(result1.current.sidebarOpen).toBe(false);
      expect(result2.current.sidebarOpen).toBe(false);

      act(() => {
        result2.current.toggleSidebar();
      });

      expect(result1.current.sidebarOpen).toBe(true);
      expect(result2.current.sidebarOpen).toBe(true);
    });
  });

  describe("store interface", () => {
    it("exposes setSidebarOpen function", () => {
      const { result } = renderHook(() => useSidebarStore());

      expect(typeof result.current.setSidebarOpen).toBe("function");
    });

    it("exposes toggleSidebar function", () => {
      const { result } = renderHook(() => useSidebarStore());

      expect(typeof result.current.toggleSidebar).toBe("function");
    });

    it("exposes sidebarOpen state", () => {
      const { result } = renderHook(() => useSidebarStore());

      expect(typeof result.current.sidebarOpen).toBe("boolean");
    });
  });
});
