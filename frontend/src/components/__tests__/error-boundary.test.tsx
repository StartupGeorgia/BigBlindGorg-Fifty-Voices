import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorBoundary } from "../error-boundary";

// Component that throws an error
function ThrowError({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("Test error message");
  }
  return <div>No error</div>;
}

describe("ErrorBoundary", () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Suppress console.error for cleaner test output
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it("renders children when there is no error", () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText("Child content")).toBeInTheDocument();
  });

  it("renders default error UI when an error occurs", () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(
      screen.getByText("An unexpected error occurred. Please try refreshing the page.")
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refresh page" })).toBeInTheDocument();
  });

  it("renders custom fallback when provided", () => {
    const customFallback = <div>Custom error fallback</div>;

    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText("Custom error fallback")).toBeInTheDocument();
    expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();
  });

  it("logs error to console when error occurs", () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      "Error Boundary caught an error:",
      expect.any(Error),
      expect.any(Object)
    );
  });

  it("calls window.location.reload when refresh button is clicked", () => {
    const reloadMock = vi.fn();
    Object.defineProperty(window, "location", {
      value: { reload: reloadMock },
      writable: true,
    });

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    const refreshButton = screen.getByRole("button", { name: "Refresh page" });
    fireEvent.click(refreshButton);

    expect(reloadMock).toHaveBeenCalled();
  });

  it("renders error icon SVG", () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    const svg = document.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveClass("text-red-500");
  });

  it("has proper styling for error container", () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    // Check for the error container's styling
    const container = screen.getByText("Something went wrong").closest("div");
    expect(container?.parentElement).toHaveClass("w-full", "max-w-md");
  });
});
