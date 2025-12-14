import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

function Button(props: { onClick: () => void; children: React.ReactNode }) {
  return <button type="button" onClick={props.onClick}>{props.children}</button>;
}

describe("Button", () => {
  it("renders label", () => {
    render(<Button onClick={() => {}}>Click</Button>);
    expect(screen.getByRole("button", { name: "Click" })).toBeTruthy();
  });

  it("fires click handler", async () => {
    const user = userEvent.setup();
    let clicks = 0;

    render(<Button onClick={() => { clicks += 1; }}>Click</Button>);
    await user.click(screen.getByRole("button", { name: "Click" }));

    expect(clicks).toBe(1);
  });
});

