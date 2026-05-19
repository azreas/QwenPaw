import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { ApiRequestError, extractErrorMessage } from "../errors.ts";

describe("webchat api errors", () => {
  it("extracts FastAPI detail", () => {
    assert.equal(
      extractErrorMessage('{"detail":"Forbidden"}', "application/json"),
      "Forbidden",
    );
  });

  it("keeps status on ApiRequestError", () => {
    const error = new ApiRequestError(429, "Too Many Requests", "");
    assert.equal(error.status, 429);
    assert.equal(error.message, "Request failed: 429 Too Many Requests");
  });
});
