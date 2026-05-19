import assert from "node:assert/strict";
import { afterEach, describe, it, mock } from "node:test";
import type { IAgentScopeRuntimeWebUISession } from "@agentscope-ai/chat";
import { SessionApi } from "./index.ts";

const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
const originalDocument = globalThis.document;
const originalLocalStorage = globalThis.localStorage;

function installBrowserGlobals() {
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      location: {
        origin: "http://localhost",
        pathname: "/webchat/chat",
      },
    },
  });
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: {
      cookie: "",
    },
  });
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: () => null,
      removeItem: () => undefined,
      setItem: () => undefined,
    },
  });
}

function restoreBrowserGlobals() {
  Object.defineProperty(globalThis, "fetch", {
    configurable: true,
    value: originalFetch,
  });
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: originalWindow,
  });
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: originalDocument,
  });
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: originalLocalStorage,
  });
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
    status: 200,
  });
}

describe("webchat session api", () => {
  afterEach(() => {
    mock.restoreAll();
    restoreBrowserGlobals();
  });

  it("fills the caller session with the backend-created id", async () => {
    installBrowserGlobals();

    const requests: string[] = [];
    mock.method(globalThis, "fetch", async (input: RequestInfo | URL) => {
      const url = String(input);
      requests.push(url);
      if (url.endsWith("/api/webchat/sessions") && requests.length === 1) {
        return jsonResponse({
          session_id: "webchat:test_user:created-1",
        });
      }
      return jsonResponse({
        sessions: [
          {
            id: "chat-created-1",
            session_id: "webchat:test_user:created-1",
            user_id: "test_user",
            channel: "webchat",
            name: "New Chat",
            created_at: "2026-05-15T00:00:00+00:00",
            updated_at: "2026-05-15T00:00:00+00:00",
            status: "idle",
            pinned: false,
            meta: {},
          },
        ],
      });
    });

    const api = new SessionApi();
    const callerSession: Partial<IAgentScopeRuntimeWebUISession> = {
      name: "",
      messages: [],
    };
    const list = await api.createSession(callerSession);

    assert.equal(callerSession.id, "chat-created-1");
    assert.deepEqual(callerSession.messages, []);
    assert.equal(list[0].id, "chat-created-1");
    assert.equal(
      (window as Window & { currentSessionId?: string }).currentSessionId,
      "webchat:test_user:created-1",
    );
  });

  it("defers URL sync until the created session is selected", async () => {
    installBrowserGlobals();

    const requests: string[] = [];
    mock.method(globalThis, "fetch", async (input: RequestInfo | URL) => {
      const url = String(input);
      requests.push(url);
      if (url.endsWith("/api/webchat/sessions") && requests.length === 1) {
        return jsonResponse({
          session_id: "webchat:test_user:created-2",
        });
      }
      if (url.endsWith("/api/webchat/sessions") && requests.length === 2) {
        return jsonResponse({
          sessions: [
            {
              id: "chat-created-2",
              session_id: "webchat:test_user:created-2",
              user_id: "test_user",
              channel: "webchat",
              name: "New Chat",
              created_at: "2026-05-15T00:00:00+00:00",
              updated_at: "2026-05-15T00:00:00+00:00",
              status: "idle",
              pinned: false,
              meta: {},
            },
          ],
        });
      }
      return jsonResponse({
        id: "chat-created-2",
        session_id: "webchat:test_user:created-2",
        user_id: "test_user",
        channel: "webchat",
        name: "New Chat",
        messages: [],
        meta: {},
      });
    });

    const api = new SessionApi();
    const createdEvents: string[] = [];
    const selectedEvents: Array<[string | null | undefined, string | null]> = [];
    api.onSessionCreated = (sessionId) => createdEvents.push(sessionId);
    api.onSessionSelected = (sessionId, realId) =>
      selectedEvents.push([sessionId, realId]);

    const callerSession: Partial<IAgentScopeRuntimeWebUISession> = {
      name: "",
      messages: [],
    };
    await api.createSession(callerSession);

    assert.deepEqual(createdEvents, []);
    await api.getSession(callerSession.id!);
    assert.deepEqual(selectedEvents, [["chat-created-2", null]]);
  });

  it("keeps local state separate for webchat and wecom bot sessions", async () => {
    installBrowserGlobals();

    let calls = 0;
    mock.method(globalThis, "fetch", async () => {
      calls += 1;
      return jsonResponse({
        sessions: [
          {
            id: "webchat-chat",
            session_id: "wecom:test_user",
            user_id: "test_user",
            channel: "webchat",
            name: calls === 1 ? "网页本地名" : "网页历史",
            created_at: "2026-05-15T00:00:00+00:00",
            updated_at: "2026-05-15T00:00:03+00:00",
            status: calls === 1 ? "running" : "idle",
            pinned: false,
            meta: {},
          },
          {
            id: "wecom-chat",
            session_id: "wecom:test_user",
            user_id: "test_user",
            channel: "wecom_tenant",
            name: "企微历史",
            created_at: "2026-05-15T00:00:00+00:00",
            updated_at: "2026-05-15T00:00:02+00:00",
            status: "idle",
            pinned: false,
            meta: {},
          },
        ],
      });
    });

    const api = new SessionApi();
    await api.updateSession({
      id: "local-webchat-temp",
      name: "网页草稿名",
    });
    await api.updateSession({
      id: "local-webchat-temp",
      realId: "webchat-chat",
      name: "网页草稿名",
      generating: true,
    } as IAgentScopeRuntimeWebUISession & {
      realId: string;
      generating: boolean;
    });

    const refreshed = await api.getSessionList();
    const webchat = refreshed.find((session) => session.id === "local-webchat-temp") as
      | (IAgentScopeRuntimeWebUISession & {
          channel?: string;
          realId?: string;
          generating?: boolean;
        })
      | undefined;
    const wecom = refreshed.find((session) => session.id === "wecom-chat") as
      | (IAgentScopeRuntimeWebUISession & {
          channel?: string;
          realId?: string;
          generating?: boolean;
        })
      | undefined;

    assert.equal(webchat?.channel, "webchat");
    assert.equal(webchat?.realId, "webchat-chat");
    assert.equal(webchat?.generating, true);
    assert.equal(webchat?.name, "网页草稿名");
    assert.equal(wecom?.channel, "wecom_tenant");
    assert.equal(wecom?.realId, undefined);
    assert.equal(wecom?.generating, false);
    assert.equal(wecom?.name, "企微历史");
  });
});
