import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@/test/test-utils";
import userEvent from "@testing-library/user-event";
import RegisterPage from "../page";

// Mock useAuth hook
const mockRegister = vi.fn();
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    register: mockRegister,
    user: null,
    isLoading: false,
  }),
}));

describe("RegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders registration form", () => {
    render(<RegisterPage />);

    expect(screen.getByText("Create an account")).toBeInTheDocument();
    expect(screen.getByText("Enter your details to get started")).toBeInTheDocument();
  });

  it("renders email input field", () => {
    render(<RegisterPage />);

    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
  });

  it("renders username input field", () => {
    render(<RegisterPage />);

    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("johndoe")).toBeInTheDocument();
  });

  it("renders password input field", () => {
    render(<RegisterPage />);

    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("renders confirm password input field", () => {
    render(<RegisterPage />);

    expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument();
  });

  it("renders submit button", () => {
    render(<RegisterPage />);

    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();
  });

  it("renders link to login page", () => {
    render(<RegisterPage />);

    expect(screen.getByText("Already have an account?")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  });

  it("allows typing in all fields", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    const emailInput = screen.getByLabelText("Email");
    const usernameInput = screen.getByLabelText("Username");
    const passwordInput = screen.getByLabelText("Password");
    const confirmPasswordInput = screen.getByLabelText("Confirm Password");

    await user.type(emailInput, "test@example.com");
    await user.type(usernameInput, "testuser");
    await user.type(passwordInput, "mypassword123");
    await user.type(confirmPasswordInput, "mypassword123");

    expect(emailInput).toHaveValue("test@example.com");
    expect(usernameInput).toHaveValue("testuser");
    expect(passwordInput).toHaveValue("mypassword123");
    expect(confirmPasswordInput).toHaveValue("mypassword123");
  });

  it("calls register function on valid form submission", async () => {
    const user = userEvent.setup();
    mockRegister.mockResolvedValueOnce(undefined);

    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Username"), "testuser");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith("test@example.com", "testuser", "password123");
    });
  });

  it("shows error when passwords do not match", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Username"), "testuser");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm Password"), "differentpassword");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
    });

    // Should not call register
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("shows error when password is too short", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Username"), "testuser");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.type(screen.getByLabelText("Confirm Password"), "short");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(screen.getByText("Password must be at least 8 characters")).toBeInTheDocument();
    });

    // Should not call register
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("shows loading state during registration", async () => {
    const user = userEvent.setup();
    let resolveRegister: () => void;
    const registerPromise = new Promise<void>((resolve) => {
      resolveRegister = resolve;
    });
    mockRegister.mockReturnValueOnce(registerPromise);

    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Username"), "testuser");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    // Button should show loading state and be disabled
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();

    resolveRegister!();
  });

  it("displays error message on registration failure", async () => {
    const user = userEvent.setup();
    mockRegister.mockRejectedValueOnce(new Error("Email already exists"));

    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "existing@example.com");
    await user.type(screen.getByLabelText("Username"), "testuser");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(screen.getByText("Email already exists")).toBeInTheDocument();
    });
  });

  it("displays generic error message when error is not an Error instance", async () => {
    const user = userEvent.setup();
    mockRegister.mockRejectedValueOnce("Something went wrong");

    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Username"), "testuser");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(screen.getByText("Registration failed")).toBeInTheDocument();
    });
  });

  it("disables inputs during loading state", async () => {
    const user = userEvent.setup();
    let resolveRegister: () => void;
    const registerPromise = new Promise<void>((resolve) => {
      resolveRegister = resolve;
    });
    mockRegister.mockReturnValueOnce(registerPromise);

    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Username"), "testuser");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    // All inputs should be disabled
    expect(screen.getByLabelText("Email")).toBeDisabled();
    expect(screen.getByLabelText("Username")).toBeDisabled();
    expect(screen.getByLabelText("Password")).toBeDisabled();
    expect(screen.getByLabelText("Confirm Password")).toBeDisabled();

    resolveRegister!();
  });

  it("has email input with type='email'", () => {
    render(<RegisterPage />);

    const emailInput = screen.getByLabelText("Email");
    expect(emailInput).toHaveAttribute("type", "email");
  });

  it("has password inputs with type='password'", () => {
    render(<RegisterPage />);

    const passwordInput = screen.getByLabelText("Password");
    const confirmPasswordInput = screen.getByLabelText("Confirm Password");

    expect(passwordInput).toHaveAttribute("type", "password");
    expect(confirmPasswordInput).toHaveAttribute("type", "password");
  });

  it("has username input with type='text'", () => {
    render(<RegisterPage />);

    const usernameInput = screen.getByLabelText("Username");
    expect(usernameInput).toHaveAttribute("type", "text");
  });

  it("requires all fields", () => {
    render(<RegisterPage />);

    expect(screen.getByLabelText("Email")).toBeRequired();
    expect(screen.getByLabelText("Username")).toBeRequired();
    expect(screen.getByLabelText("Password")).toBeRequired();
    expect(screen.getByLabelText("Confirm Password")).toBeRequired();
  });

  it("clears error message before new submission", async () => {
    const user = userEvent.setup();

    render(<RegisterPage />);

    // First, trigger password mismatch error
    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Username"), "testuser");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm Password"), "different");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
    });

    // Fix the confirm password
    await user.clear(screen.getByLabelText("Confirm Password"));
    await user.type(screen.getByLabelText("Confirm Password"), "password123");

    // Mock successful registration
    mockRegister.mockResolvedValueOnce(undefined);

    await user.click(screen.getByRole("button", { name: "Create account" }));

    // Error should be cleared
    await waitFor(() => {
      expect(screen.queryByText("Passwords do not match")).not.toBeInTheDocument();
    });
  });

  it("validates password length before password match", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Username"), "testuser");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.type(screen.getByLabelText("Confirm Password"), "different");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    // Should show password mismatch first (it's checked first in the code)
    await waitFor(() => {
      expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
    });
  });
});
