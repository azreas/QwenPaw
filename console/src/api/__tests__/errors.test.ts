import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { ApiRequestError, extractErrorMessage } from "../errors.ts";

describe("console api errors", () => {
  it("extracts FastAPI detail", () => {
    assert.equal(
      extractErrorMessage('{"detail":"Payload too large"}', "application/json"),
      "Payload too large",
    );
  });

  it("falls back to status text for empty body", () => {
    const error = new ApiRequestError(413, "Payload Too Large", "");
    assert.equal(error.message, "Request failed: 413 Payload Too Large");
    assert.equal(error.status, 413);
  });
});
