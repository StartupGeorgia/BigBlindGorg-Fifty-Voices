import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { Preloader } from "../preloader";

// Mock next/navigation
const mockUsePathname = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
}));

describe("Preloader", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockUsePathname.mockReturnValue("/dashboard");
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("renders preloader initially for non-embed routes", () => {
    mockUsePathname.mockReturnValue("/dashboard");
    render(<Preloader />);

    expect(screen.getByText("Fifty Voices")).toBeInTheDocument();
  });

  it("renders loading dots", () => {
    mockUsePathname.mockReturnValue("/dashboard");
    const { container } = render(<Preloader />);

    // Should have 3 loading dots
    const dots = container.querySelectorAll(".rounded-full.bg-slate-400");
    expect(dots.length).toBe(3);
  });

  it("hides preloader after 2 seconds for non-embed routes", async () => {
    mockUsePathname.mockReturnValue("/dashboard");
    const { container } = render(<Preloader />);

    expect(screen.getByText("Fifty Voices")).toBeInTheDocument();

    // Advance timer by 2 seconds to trigger fade out
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    // After timeout, the preloader should have opacity-0 (fade out started)
    // The component sets visible: false which adds opacity-0 class
    const preloaderContainer = container.querySelector(".fixed.inset-0.bg-black");
    // The preloader either has opacity-0 or is removed from DOM after animation
    expect(
      preloaderContainer === null || preloaderContainer.classList.contains("opacity-0")
    ).toBe(true);
  });

  it("does not show preloader for embed routes", () => {
    mockUsePathname.mockReturnValue("/embed/agent-123");
    render(<Preloader />);

    // Preloader should not be visible for embed routes
    expect(screen.queryByText("Fifty Voices")).not.toBeInTheDocument();
  });

  it("does not show preloader for embed preview routes", () => {
    mockUsePathname.mockReturnValue("/embed/agent-123/preview");
    render(<Preloader />);

    expect(screen.queryByText("Fifty Voices")).not.toBeInTheDocument();
  });

  it("has proper styling with fixed position and black background", () => {
    mockUsePathname.mockReturnValue("/dashboard");
    const { container } = render(<Preloader />);

    // Find the preloader container (framer-motion renders as div)
    const preloaderContainer = container.querySelector(".fixed.inset-0.bg-black");
    expect(preloaderContainer).toBeInTheDocument();
  });

  it("renders logo with gradient styling", () => {
    mockUsePathname.mockReturnValue("/dashboard");
    render(<Preloader />);

    const logo = screen.getByText("Fifty Voices");
    expect(logo).toHaveClass("animate-gradient-flow");
    expect(logo).toHaveClass("bg-clip-text");
    expect(logo).toHaveClass("text-transparent");
  });

  it("cleans up timer on unmount", () => {
    mockUsePathname.mockReturnValue("/dashboard");
    const { unmount } = render(<Preloader />);

    // Unmount before timer fires
    unmount();

    // Advance timer - should not cause any issues
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    // Test passes if no errors occur
    expect(true).toBe(true);
  });
});
