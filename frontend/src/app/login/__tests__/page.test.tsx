import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@/test/test-utils";
import userEvent from "@testing-library/user-event";
import LoginPage from "../page";

// Mock useAuth hook
const mockLogin = vi.fn();
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    login: mockLogin,
    user: null,
    isLoading: false,
  }),
}));

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders login form", () => {
    render(<LoginPage />);

    // Check for the description text which is unique to the heading
    expect(screen.getByText("Enter your credentials to access your account")).toBeInTheDocument();
    // Check for submit button
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("renders Fifty Voices branding", () => {
    render(<LoginPage />);

    expect(screen.getByText("Fifty Voices")).toBeInTheDocument();
  });

  it("renders email input field", () => {
    render(<LoginPage />);

    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
  });

  it("renders password input field", () => {
    render(<LoginPage />);

    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("renders submit button", () => {
    render(<LoginPage />);

    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("renders link to register page", () => {
    render(<LoginPage />);

    expect(screen.getByText("Don't have an account?")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign up" })).toHaveAttribute("href", "/register");
  });

  it("allows typing in email field", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    const emailInput = screen.getByLabelText("Email");
    await user.type(emailInput, "test@example.com");

    expect(emailInput).toHaveValue("test@example.com");
  });

  it("allows typing in password field", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    const passwordInput = screen.getByLabelText("Password");
    await user.type(passwordInput, "mypassword123");

    expect(passwordInput).toHaveValue("mypassword123");
  });

  it("calls login function on form submission", async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValueOnce(undefined);

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("test@example.com", "password123");
    });
  });

  it("shows loading state during login", async () => {
    const user = userEvent.setup();
    // Create a promise that doesn't resolve immediately
    let resolveLogin: () => void;
    const loginPromise = new Promise<void>((resolve) => {
      resolveLogin = resolve;
    });
    mockLogin.mockReturnValueOnce(loginPromise);

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    // Button should show loading state
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();

    // Resolve the login
    resolveLogin!();
  });

  it("displays error message on login failure", async () => {
    const user = userEvent.setup();
    mockLogin.mockRejectedValueOnce(new Error("Invalid credentials"));

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "wrong@example.com");
    await user.type(screen.getByLabelText("Password"), "wrongpassword");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    });
  });

  it("displays generic error message when error is not an Error instance", async () => {
    const user = userEvent.setup();
    mockLogin.mockRejectedValueOnce("Something went wrong");

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByText("Login failed")).toBeInTheDocument();
    });
  });

  it("clears error message before new submission", async () => {
    const user = userEvent.setup();
    mockLogin.mockRejectedValueOnce(new Error("Invalid credentials"));
    mockLogin.mockResolvedValueOnce(undefined);

    render(<LoginPage />);

    // First failed attempt
    await user.type(screen.getByLabelText("Email"), "wrong@example.com");
    await user.type(screen.getByLabelText("Password"), "wrongpassword");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    });

    // Clear inputs and try again
    await user.clear(screen.getByLabelText("Email"));
    await user.clear(screen.getByLabelText("Password"));
    await user.type(screen.getByLabelText("Email"), "correct@example.com");
    await user.type(screen.getByLabelText("Password"), "correctpassword");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    // Error should be cleared during submission
    await waitFor(() => {
      expect(screen.queryByText("Invalid credentials")).not.toBeInTheDocument();
    });
  });

  it("disables inputs during loading state", async () => {
    const user = userEvent.setup();
    let resolveLogin: () => void;
    const loginPromise = new Promise<void>((resolve) => {
      resolveLogin = resolve;
    });
    mockLogin.mockReturnValueOnce(loginPromise);

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    // Inputs should be disabled
    expect(screen.getByLabelText("Email")).toBeDisabled();
    expect(screen.getByLabelText("Password")).toBeDisabled();

    resolveLogin!();
  });

  it("has email input with type='email'", () => {
    render(<LoginPage />);

    const emailInput = screen.getByLabelText("Email");
    expect(emailInput).toHaveAttribute("type", "email");
  });

  it("has password input with type='password'", () => {
    render(<LoginPage />);

    const passwordInput = screen.getByLabelText("Password");
    expect(passwordInput).toHaveAttribute("type", "password");
  });

  it("requires email field", () => {
    render(<LoginPage />);

    const emailInput = screen.getByLabelText("Email");
    expect(emailInput).toBeRequired();
  });

  it("requires password field", () => {
    render(<LoginPage />);

    const passwordInput = screen.getByLabelText("Password");
    expect(passwordInput).toBeRequired();
  });

  it("renders with proper dark background styling", () => {
    const { container } = render(<LoginPage />);

    const wrapper = container.querySelector(".bg-black");
    expect(wrapper).toBeInTheDocument();
  });
});
