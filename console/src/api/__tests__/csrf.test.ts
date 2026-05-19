import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { appendCsrfHeader, readCsrfToken } from "../csrf.ts";

describe("console csrf helper", () => {
  it("reads qwenpaw_session from cookie text", () => {
    assert.equal(
      readCsrfToken("theme=dark; qwenpaw_session=abc%20123; other=x"),
      "abc 123",
    );
  });

  it("adds x-csrf-token only when session cookie exists", () => {
    const headers = new Headers();
    appendCsrfHeader(headers, "qwenpaw_session=token");
    assert.equal(headers.get("X-CSRF-Token"), "token");

    const empty = new Headers();
    appendCsrfHeader(empty, "theme=dark");
    assert.equal(empty.has("X-CSRF-Token"), false);
  });
});
