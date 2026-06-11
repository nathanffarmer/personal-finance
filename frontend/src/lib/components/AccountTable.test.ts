import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/svelte";
import AccountTable from "./AccountTable.svelte";
import type { Account } from "$api/monarch";

function acct(overrides: Partial<Account>): Account {
  return {
    id: "x",
    name: "X",
    type: "depository",
    subtype: null,
    institution: null,
    balance_current: 0,
    balance_available: null,
    currency: "USD",
    is_hidden: false,
    updated_at: null,
    ...overrides,
  };
}

describe("AccountTable", () => {
  it("groups accounts by type and renders a per-group subtotal", () => {
    render(AccountTable, {
      props: {
        accounts: [
          acct({ id: "1", name: "Checking", type: "depository", balance_current: 5000 }),
          acct({ id: "2", name: "Savings", type: "depository", balance_current: 3000 }),
          acct({
            id: "3",
            name: "Brokerage",
            type: "investment",
            balance_current: 200000,
          }),
        ],
      },
    });
    expect(screen.getByText("Cash")).toBeInTheDocument();
    expect(screen.getByText("Investments")).toBeInTheDocument();
    expect(screen.getByText("Checking")).toBeInTheDocument();
    // Cash subtotal = 5000 + 3000.
    expect(screen.getByText("$8,000")).toBeInTheDocument();
  });

  it("excludes hidden accounts", () => {
    render(AccountTable, {
      props: {
        accounts: [
          acct({ id: "1", name: "Visible", balance_current: 100 }),
          acct({ id: "2", name: "Secret", balance_current: 999, is_hidden: true }),
        ],
      },
    });
    expect(screen.getByText("Visible")).toBeInTheDocument();
    expect(screen.queryByText("Secret")).not.toBeInTheDocument();
  });

  it("renders nothing for an empty account list", () => {
    const { container } = render(AccountTable, { props: { accounts: [] } });
    expect(container.querySelectorAll("table")).toHaveLength(0);
  });
});
