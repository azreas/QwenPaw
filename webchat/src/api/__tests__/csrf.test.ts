import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { appendCsrfHeader, readCsrfToken } from "../csrf.ts";

describe("webchat csrf helper", () => {
  it("reads qwenpaw_session from cookie text", () => {
    assert.equal(readCsrfToken("qwenpaw_session=token"), "token");
  });

  it("does not overwrite caller supplied csrf header", () => {
    const headers = new Headers({ "X-CSRF-Token": "caller" });
    appendCsrfHeader(headers, "qwenpaw_session=cookie");
    assert.equal(headers.get("X-CSRF-Token"), "caller");
  });
});
