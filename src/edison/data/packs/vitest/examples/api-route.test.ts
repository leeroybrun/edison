import { describe, it, expect } from "vitest";

// Minimal illustrative pattern: test a real handler boundary
// using Web Request/Response objects (no internal mocking).
async function handleGetItems(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const page = Number(url.searchParams.get("page") ?? "1");

  if (!Number.isFinite(page) || page < 1) {
    return Response.json({ error: "Validation failed" }, { status: 400 });
  }

  return Response.json({ data: [{ id: "1", name: "Item" }], meta: { page } }, { status: 200 });
}

describe("route handler", () => {
  it("returns 400 on invalid query", async () => {
    const req = new Request("https://example.test/api/items?page=0");
    const res = await handleGetItems(req);

    expect(res.status).toBe(400);
    expect(await res.json()).toMatchObject({ error: "Validation failed" });
  });

  it("returns 200 with envelope on success", async () => {
    const req = new Request("https://example.test/api/items?page=1");
    const res = await handleGetItems(req);

    expect(res.status).toBe(200);
    expect(await res.json()).toMatchObject({
      data: [{ id: "1", name: "Item" }],
      meta: { page: 1 },
    });
  });
});

