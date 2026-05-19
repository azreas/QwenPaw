import assert from "node:assert/strict";
import { describe, it, mock } from "node:test";
import { rootRequest } from "../rootRequest.ts";

describe("rootRequest allowed status codes", () => {
  it("rejects 503 by default", async () => {
    mock.method(global, "fetch", () =>
      Promise.resolve(
        new Response(JSON.stringify({ ready: false, status: "down" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    let threw = false;
    try {
      await rootRequest("/ready");
    } catch {
      threw = true;
    }
    assert.equal(threw, true);

    mock.reset();
  });

  it("accepts 503 when allowed and parses JSON body", async () => {
    mock.method(global, "fetch", () =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            ready: false,
            status: "degraded",
            components: [
              { name: "storage", status: "ok" },
              { name: "redis", status: "down" },
            ],
          }),
          {
            status: 503,
            headers: { "Content-Type": "application/json" },
          },
        ),
      ),
    );

    const result = await rootRequest("/ready", { allowedStatuses: [503] });

    assert.deepEqual(result, {
      ready: false,
      status: "degraded",
      components: [
        { name: "storage", status: "ok" },
        { name: "redis", status: "down" },
      ],
    });

    mock.reset();
  });

  it("still throws for status codes not in allowed list", async () => {
    mock.method(global, "fetch", () =>
      Promise.resolve(
        new Response(JSON.stringify({ detail: "Unauthorized" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    let threw = false;
    try {
      await rootRequest("/ready", { allowedStatuses: [503] });
    } catch {
      threw = true;
    }
    assert.equal(threw, true);

    mock.reset();
  });

  it("handles text response for non-JSON content types", async () => {
    mock.method(global, "fetch", () =>
      Promise.resolve(
        new Response("plain text error", {
          status: 503,
          headers: { "Content-Type": "text/plain" },
        }),
      ),
    );

    const result = await rootRequest("/ready", { allowedStatuses: [503] });

    assert.equal(result, "plain text error");

    mock.reset();
  });
});
