import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useIsMobile } from "../use-mobile";

describe("useIsMobile", () => {
  let matchMediaMock: ReturnType<typeof vi.fn>;
  let addEventListenerMock: ReturnType<typeof vi.fn>;
  let removeEventListenerMock: ReturnType<typeof vi.fn>;
  let originalInnerWidth: number;

  beforeEach(() => {
    addEventListenerMock = vi.fn();
    removeEventListenerMock = vi.fn();
    originalInnerWidth = window.innerWidth;

    matchMediaMock = vi.fn().mockReturnValue({
      matches: false,
      addEventListener: addEventListenerMock,
      removeEventListener: removeEventListenerMock,
    });

    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: matchMediaMock,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: originalInnerWidth,
    });
  });

  it("returns false for desktop viewport (width >= 768px)", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 1024,
    });

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(false);
  });

  it("returns true for mobile viewport (width < 768px)", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 500,
    });

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(true);
  });

  it("returns false for exactly 768px viewport", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 768,
    });

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(false);
  });

  it("returns true for 767px viewport (edge case)", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 767,
    });

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(true);
  });

  it("uses correct media query breakpoint", () => {
    renderHook(() => useIsMobile());

    expect(matchMediaMock).toHaveBeenCalledWith("(max-width: 767px)");
  });

  it("adds event listener on mount", () => {
    renderHook(() => useIsMobile());

    expect(addEventListenerMock).toHaveBeenCalledWith("change", expect.any(Function));
  });

  it("removes event listener on unmount", () => {
    const { unmount } = renderHook(() => useIsMobile());

    unmount();

    expect(removeEventListenerMock).toHaveBeenCalledWith("change", expect.any(Function));
  });

  it("updates value when media query changes", async () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 1024,
    });

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(false);

    // Simulate viewport change to mobile
    act(() => {
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        value: 500,
      });

      // Get the onChange handler and call it
      const onChangeHandler = addEventListenerMock.mock.calls[0][1];
      onChangeHandler();
    });

    expect(result.current).toBe(true);
  });

  it("handles resize from mobile to desktop", async () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 500,
    });

    const { result } = renderHook(() => useIsMobile());

    expect(result.current).toBe(true);

    // Simulate viewport change to desktop
    act(() => {
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        value: 1024,
      });

      const onChangeHandler = addEventListenerMock.mock.calls[0][1];
      onChangeHandler();
    });

    expect(result.current).toBe(false);
  });

  it("returns boolean (not undefined after initial render)", async () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 1024,
    });

    const { result } = renderHook(() => useIsMobile());

    // Due to the !! conversion, undefined becomes false
    expect(typeof result.current).toBe("boolean");
  });

  it("handles multiple remounts correctly", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      value: 500,
    });

    const { result, unmount } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);

    unmount();

    const { result: result2 } = renderHook(() => useIsMobile());
    expect(result2.current).toBe(true);
  });
});
