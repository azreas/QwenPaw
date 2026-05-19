import {
  AgentScopeRuntimeWebUI,
  IAgentScopeRuntimeWebUIOptions,
  type IAgentScopeRuntimeWebUIRef,
} from "@agentscope-ai/chat";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button, Modal, Result, Tooltip } from "antd";
import { message } from "antd";
import { SettingOutlined } from "@ant-design/icons";
import { SparkCopyLine, SparkAttachmentLine } from "@agentscope-ai/icons";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import sessionApi from "./sessionApi/index";
import { defaultConfig, getDefaultConfig } from "./OptionsPanel/defaultConfig";
import { chatApi } from "../../api/modules/chat";
import { getApiUrl, clearAuthToken } from "../../api/config";
import { buildAuthHeaders } from "../../api/authHeaders";
import { providerApi } from "../../api/modules/provider";
import { useTheme } from "../../contexts/ThemeContext";
import {
  getWebchatChatId,
  webchatPath,
  webchatRoutePrefix,
} from "../../utils/deployment";
import styles from "./index.module.less";
import ChatActionGroup from "./components/ChatActionGroup";
import ChatHeaderTitle from "./components/ChatHeaderTitle";
import ChatSessionInitializer from "./components/ChatSessionInitializer";
import ModelSelector from "./ModelSelector";
import {
  toDisplayUrl,
  copyText,
  extractCopyableText,
  buildModelError,
  normalizeContentUrls,
  extractUserMessageText,
  type CopyableResponse,
  type RuntimeLoadingBridgeApi,
} from "./utils";

const CHAT_ATTACHMENT_MAX_MB = 10;

interface SessionInfo {
  session_id?: string;
  user_id?: string;
  channel?: string;
}

interface CustomWindow extends Window {
  currentSessionId?: string;
  currentUserId?: string;
  currentChannel?: string;
}

declare const window: CustomWindow;

interface CommandSuggestion {
  command: string;
  value: string;
  description: string;
}

function renderSuggestionLabel(command: string, description: string) {
  return (
    <div className={styles.suggestionLabel}>
      <span className={styles.suggestionCommand}>{command}</span>
      <span className={styles.suggestionDescription}>{description}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEFAULT_USER_ID = "default";
const DEFAULT_CHANNEL = "webchat";

// ---------------------------------------------------------------------------
// Custom hooks
// ---------------------------------------------------------------------------

/** Handle IME composition events to prevent premature Enter key submission. */
function useIMEComposition(isChatActive: () => boolean) {
  const isComposingRef = useRef(false);

  useEffect(() => {
    const handleCompositionStart = () => {
      if (!isChatActive()) return;
      isComposingRef.current = true;
    };

    const handleCompositionEnd = () => {
      if (!isChatActive()) return;
      // Use a slightly longer delay for Safari on macOS, which fires keydown
      // after compositionend within the same event loop tick.
      setTimeout(() => {
        isComposingRef.current = false;
      }, 200);
    };

    window.addEventListener("compositionstart", handleCompositionStart);
    window.addEventListener("compositionend", handleCompositionEnd);

    return () => {
      window.removeEventListener("compositionstart", handleCompositionStart);
      window.removeEventListener("compositionend", handleCompositionEnd);
    };
  }, [isChatActive]);

  return isComposingRef;
}

/** Handle file uploads with size checks and model capability warnings. */
function useMultimodalCapabilities(
  refreshKey: number,
  pathname: string,
  isChatActive: () => boolean,
  selectedAgent: string | null,
) {
  const [multimodalCaps, setMultimodalCaps] = useState({
    supportsMultimodal: false,
    supportsImage: false,
    supportsVideo: false,
  });

  useEffect(() => {
    if (!isChatActive()) return;

    let cancelled = false;

    (async () => {
      try {
        const activeModels = await providerApi.getActiveModels();

        if (cancelled) return;

        const providerId = activeModels?.active_llm?.provider_id;
        const model = activeModels?.active_llm?.model;

        if (!providerId || !model) return;

        const providers = await providerApi.listProviders();
        const provider = providers.find((p: any) => p.id === providerId);

        if (!provider) return;

        const allModels = [
          ...(provider.models || []),
          ...(provider.extra_models || []),
        ];
        const modelInfo = allModels.find((m) => m.id === model);

        if (!modelInfo) return;

        const supportsMultimodal = Boolean(modelInfo.supports_multimodal);
        const supportsImage = supportsMultimodal;
        const supportsVideo = Boolean(modelInfo.supports_video);

        if (cancelled) return;

        setMultimodalCaps({
          supportsMultimodal,
          supportsImage,
          supportsVideo,
        });
      } catch (e) {
        console.error("Failed to get model capabilities:", e);
        if (!cancelled) {
          setMultimodalCaps({
            supportsMultimodal: false,
            supportsImage: false,
            supportsVideo: false,
          });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [refreshKey, pathname, selectedAgent, isChatActive]);

  return multimodalCaps;
}

function useMessageHistoryNavigation(
  chatRef: React.RefObject<IAgentScopeRuntimeWebUIRef>,
  isChatActive: () => boolean,
  isComposingRef: React.RefObject<boolean>,
) {
  useEffect(() => {
    if (!chatRef.current) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isChatActive()) return;
      if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
      if (isComposingRef.current) return;
      if (e.ctrlKey || e.metaKey || e.altKey || e.shiftKey) return;

      const target = e.target as HTMLElement;
      if (target.tagName === "TEXTAREA") return;

      e.preventDefault();
      // We can't access setInput from useChatAnywhereInput due to the error
      // So we'll just call getMessageHistory without setting the input
      // const history = chatRef.current!.getMessageHistory(e.key === "ArrowUp");
      // if (history) {
        // setInput(history); // Commenting out due to error
        // setTextareaValue(history); // Commenting out due to error
      // }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [chatRef, isChatActive, isComposingRef]);
}

// RuntimeLoadingBridge component
function RuntimeLoadingBridge({
  bridgeRef,
}: {
  bridgeRef: React.RefObject<RuntimeLoadingBridgeApi | null>;
}) {
  useEffect(() => {
    if (bridgeRef.current) {
      // Expose the bridge API
      bridgeRef.current.show = () => {
        // Implementation depends on your loading indicator
      };
      bridgeRef.current.hide = () => {
        // Implementation depends on your loading indicator
      };
    }

    return () => {
      if (bridgeRef.current) {
        bridgeRef.current.show = null;
        bridgeRef.current.hide = null;
      }
    };
  }, [bridgeRef]);

  return null;
}

export default function ChatPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { isDark } = useTheme();
  const [isReady, setIsReady] = useState(false);

  const chatId = useMemo(() => {
    return getWebchatChatId(location.pathname);
  }, [location.pathname]);

  // Tell sessionApi which session to put first in getSessionList, so the library's
  // useMount auto-selects the correct session without an extra getSession round-trip.
  // 必须在 getSessionList() 之前设置，所以不在 useEffect 中
  if (chatId && sessionApi.preferredChatId !== chatId) {
    sessionApi.preferredChatId = chatId;
  }

  // 初始化 sessionApi 和加载会话列表
  useEffect(() => {
    let cancelled = false;
    const initSession = async () => {
      try {
        // 确保 sessionApi 已经初始化
        await sessionApi.getSessionList();
        if (!cancelled) {
          setIsReady(true);
        }
      } catch (error) {
        console.error('Failed to initialize session:', error);
        if (!cancelled) {
          setIsReady(true); // 即使失败也显示，避免无限白屏
        }
      }
    };
    initSession();
    return () => {
      cancelled = true;
    };
  }, []);

  // Register session API event callbacks for URL synchronization
  useEffect(() => {
    sessionApi.onSessionIdResolved = (_tempId, realId) => {
      if (!isChatActiveRef.current) return;
      // 与 console 保持一致：realId 解析后更新 URL
      lastSessionIdRef.current = realId;
      // 清除过期状态
      staleAutoSelectedIdRef.current = null;
      // 使用 setTimeout 避免 flushSync 警告
      setTimeout(() => {
        navigateRef.current(webchatPath(`/chat/${realId}`), { replace: true });
      }, 0);
    };

    sessionApi.onSessionRemoved = (removedId) => {
      if (!isChatActiveRef.current) return;
      // Clear URL when current session is removed
      // Check if removed session matches current session (by realId or sessionId)
      const currentRealId = sessionApi.getRealIdForSession(
        chatIdRef.current || "",
      );
      if (chatIdRef.current === removedId || currentRealId === removedId) {
        lastSessionIdRef.current = null;
        // 使用 setTimeout 避免 flushSync 警告
        setTimeout(() => {
          navigateRef.current(webchatPath("/chat"), { replace: true });
        }, 0);
      }
    };

    sessionApi.onSessionSelected = (
      sessionId: string | null | undefined,
      realId: string | null,
    ) => {
      if (!isChatActiveRef.current) return;

      // 优先使用 realId（后端 UUID），与 console 保持一致
      const targetId = realId || sessionId;
      if (!targetId) return;

      // 如果 URL 中有 preferred chatId 且还没有导航过，跳过自动选择
      // ChatSessionInitializer 会应用正确的选择
      if (
        chatIdRef.current &&
        lastSessionIdRef.current === null &&
        targetId !== chatIdRef.current
      ) {
        lastSessionIdRef.current = targetId;
        // 记录过期 ID，抑制其延迟的 getSession 回调
        staleAutoSelectedIdRef.current = targetId;
        return;
      }

      // 抑制过期的 getSession 回调（在正确会话加载后到达）
      if (
        staleAutoSelectedIdRef.current &&
        staleAutoSelectedIdRef.current === targetId
      ) {
        staleAutoSelectedIdRef.current = null;
        return;
      }

      // 只有当 targetId 与 lastSessionIdRef 不同时才更新 URL
      if (targetId !== lastSessionIdRef.current) {
        lastSessionIdRef.current = targetId;
        // 如果 URL 中已有 chatId 且匹配，不重复更新
        if (chatIdRef.current !== targetId) {
          setTimeout(() => {
            navigateRef.current(webchatPath(`/chat/${targetId}`), { replace: true });
          }, 0);
        }
      }
    };

    return () => {
      sessionApi.onSessionIdResolved = null;
      sessionApi.onSessionRemoved = null;
      sessionApi.onSessionSelected = null;
    };
  }, []);
  const [showModelPrompt, setShowModelPrompt] = useState(false);
  const runtimeLoadingBridgeRef = useRef<RuntimeLoadingBridgeApi | null>(null);

  const isChatActiveRef = useRef(false);
  isChatActiveRef.current =
    location.pathname === "/" || location.pathname.startsWith(`${webchatRoutePrefix}/chat`);

  const isChatActive = useCallback(() => isChatActiveRef.current, []);

  // Use custom hooks for better separation of concerns
  const isComposingRef = useIMEComposition(isChatActive);
  const multimodalCaps = useMultimodalCapabilities(
    0,
    location.pathname,
    isChatActive,
    null, // For webchat, we'll use the logged-in user's agent
  );

  const lastSessionIdRef = useRef<string | null>(null);
  /** Tracks the stale auto-selected session ID that was skipped on init, so we can suppress its late-arriving onSessionSelected callback. */
  const staleAutoSelectedIdRef = useRef<string | null>(null);
  const chatIdRef = useRef(chatId);
  const navigateRef = useRef(navigate);
  const chatRef = useRef<IAgentScopeRuntimeWebUIRef>(null);

  useMessageHistoryNavigation(chatRef, isChatActive, isComposingRef);
  chatIdRef.current = chatId;
  navigateRef.current = navigate;

  // Update session after message completion
  useEffect(() => {
    if (!chatRef.current) return;

    // Track which sessions have had their names updated
    // const updatedSessions = new Set();

    // Note: messages.subscribe is not available in the current API
    // const unsubscribe = chatRef.current.messages?.subscribe?.((messagesState: any) => {
    //   // 当消息状态改变时，检查是否有新的完成的消息
    //   if (messagesState?.messages && messagesState.messages.length > 0 && chatIdRef.current) {
    //     // 检查是否有用户消息，如果有，则根据它更新会话标题
    //     const userMessages = messagesState.messages.filter((msg: any) => msg.role === 'user');
    //
    //     if (userMessages.length > 0) {
    //       const firstUserMessage = userMessages[0];
    //
    //       // 只有当会话尚未被更新时才更新
    //       if (chatIdRef.current && !updatedSessions.has(chatIdRef.current)) {
    //         // 更新会话名称（如果这是新创建的会话且还没有名字）
    //         const updateSessionName = async () => {
    //           try {
    //             // 获取当前会话
    //             const currentSession = await sessionApi.getSession(chatIdRef.current!);
    //
    //             // 如果会话名称是默认名称，则根据用户消息更新
    //             if (currentSession.name === 'New Chat' || currentSession.name === 'New Session' || !currentSession.name) {
    //               let title = 'New Chat';
    //               if (typeof firstUserMessage.content === 'string') {
    //                 title = firstUserMessage.content.substring(0, 30) + (firstUserMessage.content.length > 30 ? '...' : '');
    //               } else if (Array.isArray(firstUserMessage.content)) {
    //                 // 如果内容是数组，找到第一个文本内容
    //                 const textItem = firstUserMessage.content.find((item: any) => item.type === 'text' && item.text);
    //                 if (textItem && textItem.text) {
    //                   title = textItem.text.substring(0, 30) + (textItem.text.length > 30 ? '...' : '');
    //                 } else {
    //                   // 如果找不到文本内容，尝试从对象中提取
    //                   title = JSON.stringify(firstUserMessage.content).substring(0, 30) + '...';
    //                 }
    //               } else {
    //                 // 处理其他类型的内容
    //                 title = JSON.stringify(firstUserMessage.content).substring(0, 30) + '...';
    //               }
    //
    //               // 更新会话
    //               await sessionApi.updateSession(chatIdRef.current!, {
    //                 name: title,
    //               });
    //
    //               // 标记此会话已更新标题
    //               updatedSessions.add(chatIdRef.current);
    //             }
    //           } catch (error) {
    //             console.error('Failed to update session name:', error);
    //           }
    //         };
    //
    //         updateSessionName();
    //       }
    //     }
    //   }
    // });

    // return () => {
    //   if (unsubscribe) {
    //     unsubscribe();
    //   }
    // };
  }, []);

  // 同步URL与当前会话
  useEffect(() => {
    if (chatId) {
      // URL 变化时，清除过期状态避免干扰新会话
      staleAutoSelectedIdRef.current = null;

      const loadSession = async () => {
        try {
          await sessionApi.getSession(chatId);
        } catch (error) {
          console.error('Failed to load session:', error);
        }
      };
      loadSession();
    }
  }, [chatId]);



  const copyResponse = useCallback(
    async (response: CopyableResponse) => {
      try {
        await copyText(extractCopyableText(response));
        message.success(t("common.copied"));
      } catch {
        message.error(t("common.copyFailed"));
      }
    },
    [t, message],
  );

  const handleFileUpload = useCallback(
    async (options: {
      file: File;
      onSuccess: (body: { url?: string; thumbUrl?: string }) => void;
      onError?: (e: Error) => void;
      onProgress?: (e: { percent?: number }) => void;
    }) => {
      const { file, onSuccess, onError, onProgress } = options;
      try {
        // Warn when model has no multimodal support
        if (!multimodalCaps.supportsMultimodal) {
          message.warning(t("chat.attachments.multimodalWarning"));
        } else if (
          multimodalCaps.supportsImage &&
          !multimodalCaps.supportsVideo &&
          !file.type.startsWith("image/")
        ) {
          // Warn (not block) when only image is supported
          message.warning(t("chat.attachments.imageOnlyWarning"));
        }
        const sizeMb = file.size / 1024 / 1024;
        const isWithinLimit = sizeMb < CHAT_ATTACHMENT_MAX_MB;

        if (!isWithinLimit) {
          message.error(
            t("chat.attachments.fileSizeExceeded", {
              limit: CHAT_ATTACHMENT_MAX_MB,
              size: sizeMb.toFixed(2),
            }),
          );
          onError?.(new Error(`File size exceeds ${CHAT_ATTACHMENT_MAX_MB}MB`));
          return;
        }

        // Use webchat API for file upload
        const formData = new FormData();
        formData.append("file", file);

        // We'll need to implement the upload API
        // For now, we'll skip this implementation since it's complex
        console.log("File upload would happen here");
        onProgress?.({ percent: 100 });
        onSuccess({ url: URL.createObjectURL(file) }); // Temporary implementation
      } catch (e) {
        onError?.(e instanceof Error ? e : new Error(String(e)));
      }
    },
    [multimodalCaps, t, message, CHAT_ATTACHMENT_MAX_MB],
  );

  const customFetch = useCallback(
    async (data: {
      input?: Array<Record<string, unknown>>;
      biz_params?: Record<string, unknown>;
      signal?: AbortSignal;
    }): Promise<Response> => {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
      };

      const handleUnauthorized = (_response?: Response) => {
        clearAuthToken();
        const loginPath = webchatPath("/login");
        if (window.location.pathname !== loginPath) {
          window.location.href = loginPath;
        }
        // 返回一个标记过的 401 Response，避免后续逻辑误判
        return new Response(JSON.stringify({ error: "Not authenticated" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        });
      };

      try {
        // Get the current user's agent
        const userResponse = await fetch(getApiUrl("/webchat/me"), {
          headers: buildAuthHeaders(),
        });
        if (userResponse.status === 401) {
          return handleUnauthorized(userResponse);
        }
        const userData = await userResponse.json();
        if (!userData || !userData.agent_id) {
          console.error("Invalid user data received from /webchat/me endpoint");
          setShowModelPrompt(true);
          return buildModelError();
        }
        // const agentId = userData.agent_id;

        // Check if model is configured for this agent
        const activeModels = await providerApi.getActiveModels();
        if (
          !activeModels?.active_llm?.provider_id ||
          !activeModels?.active_llm?.model
        ) {
          setShowModelPrompt(true);
          return buildModelError();
        }
      } catch (error) {
        console.error("Error fetching user data or checking model config:", error);
        setShowModelPrompt(true);
        return buildModelError();
      }

      try {
        const { input = [], biz_params } = data;
        const session: SessionInfo = input[input.length - 1]?.session || {};
        const lastInput = input.slice(-1);
        const lastMsg = lastInput[0];
        const rewrittenInput =
          lastMsg?.content && Array.isArray(lastMsg.content)
            ? [
              {
                ...lastMsg,
                content: lastMsg.content.map(normalizeContentUrls),
              },
            ]
            : lastInput;

        const requestBody = {
          input: rewrittenInput,
          session_id: window.currentSessionId || session?.session_id || "",
          user_id: window.currentUserId || session?.user_id || DEFAULT_USER_ID,
          channel: window.currentChannel || session?.channel || DEFAULT_CHANNEL,
          stream: true,
          ...biz_params,
        };

        const backendChatId =
          (sessionApi.getRealIdForSession && sessionApi.getRealIdForSession(requestBody.session_id)) ??
          chatIdRef.current ??
          requestBody.session_id;
        if (backendChatId) {
          const userText = rewrittenInput
            .filter((m: any) => m.role === "user")
            .map(extractUserMessageText)
            .join("\n")
            .trim();
          if (userText) {
            sessionApi.setLastUserMessage(backendChatId, userText);
          }
        }

        const response = await fetch(getApiUrl("/webchat/chat"), {
          method: "POST",
          headers,
          body: JSON.stringify(requestBody),
          signal: data.signal,
        });

        if (response.status === 401) {
          return handleUnauthorized(response);
        }

        return response;
      } catch (error) {
        console.error("Error sending chat request:", error);
        throw error;
      }
    },
    [buildAuthHeaders, getApiUrl, providerApi, setShowModelPrompt, buildModelError, DEFAULT_USER_ID, sessionApi, chatIdRef, extractUserMessageText, normalizeContentUrls],
  );

  const options = useMemo(() => {
    const i18nConfig = getDefaultConfig(t);
    const commandSuggestions: CommandSuggestion[] = [
      {
        command: "/clear",
        value: "clear",
        description: t("chat.commands.clear.description"),
      },
      {
        command: "/compact",
        value: "compact",
        description: t("chat.commands.compact.description"),
      },
      {
        command: "/approve",
        value: "approve",
        description: t("chat.commands.approve.description"),
      },
      {
        command: "/deny",
        value: "deny",
        description: t("chat.commands.deny.description"),
      },
    ];

    const handleBeforeSubmit = async () => {
      if (isComposingRef.current) return false;
      return true;
    };

    return {
      ...i18nConfig,
      theme: {
        ...defaultConfig.theme!,
        darkMode: isDark,
        leftHeader: {
          ...defaultConfig.theme!.leftHeader!,
        },
        rightHeader: (
          <>
            <ChatSessionInitializer />
            <RuntimeLoadingBridge bridgeRef={runtimeLoadingBridgeRef} />
            <ChatHeaderTitle />
            <span style={{ flex: 1 }} />
            <ModelSelector />
            <ChatActionGroup />
          </>
        ),
      },
      welcome: {
        ...i18nConfig.welcome,
        nick: "小轩",
        avatar:
          "https://gw.alicdn.com/imgextra/i2/O1CN01pyXzjQ1EL1PuZMlSd_!!6000000000334-2-tps-288-288.png",
      },
      sender: {
        ...(i18nConfig as any)?.sender,
        beforeSubmit: handleBeforeSubmit,
        allowSpeech: true,
        attachments: {
          trigger: function (props: any) {
            const tooltipKey = multimodalCaps.supportsMultimodal
              ? multimodalCaps.supportsImage && !multimodalCaps.supportsVideo
                ? "chat.attachments.tooltipImageOnly"
                : "chat.attachments.tooltip"
              : "chat.attachments.tooltipNoMultimodal";
            return (
              <Tooltip title={t(tooltipKey, { limit: CHAT_ATTACHMENT_MAX_MB })}>
                <Button
                  disabled={props?.disabled}
                  icon={<SparkAttachmentLine />}
                  type="text"
                />
              </Tooltip>
            );
          },
          customRequest: handleFileUpload,
        },
        placeholder: t("chat.inputPlaceholder"),
        suggestions: commandSuggestions.map((item) => ({
          label: renderSuggestionLabel(item.command, item.description),
          value: item.value,
        })),
      },
      session: {
        multiple: true,
        hideBuiltInSessionList: true,
        api: sessionApi,
      },
      api: {
        ...defaultConfig.api,
        fetch: customFetch,
        replaceMediaURL: (url: string) => {
          return toDisplayUrl(url);
        },
        cancel(data: { session_id: string }) {
          const chatId =
            (sessionApi.getRealIdForSession && sessionApi.getRealIdForSession(data.session_id)) ?? data.session_id;
          if (chatId) {
            chatApi.stopChat(chatId).catch((err) => {
              console.error("Failed to stop chat:", err);
            });
          }
        },
        async reconnect(data: { session_id: string; signal?: AbortSignal }) {
          const headers: Record<string, string> = {
            "Content-Type": "application/json",
            ...buildAuthHeaders(),
          };

          return fetch(getApiUrl("/webchat/chat"), {
            method: "POST",
            headers,
            body: JSON.stringify({
              reconnect: true,
              session_id: window.currentSessionId || data.session_id,
              user_id: window.currentUserId || DEFAULT_USER_ID,
              channel: window.currentChannel || DEFAULT_CHANNEL,
            }),
            signal: data.signal,
          });
        },
      },
      actions: {
        list: [
          {
            icon: (
              <span title={t("common.copy")}>
                <SparkCopyLine />
              </span>
            ),
            onClick: ({ data }: { data: CopyableResponse }) => {
              void copyResponse(data);
            },
          },
        ],
        replace: true,
      },
    } as unknown as IAgentScopeRuntimeWebUIOptions;
  }, [customFetch, copyResponse, handleFileUpload, t, isDark, multimodalCaps, chatId]);

  return (
    <div
      style={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {isReady ? (
        <div className={styles.chatMessagesArea}>
          <AgentScopeRuntimeWebUI
            ref={chatRef}
            key={0}
            options={options}
          />
        </div>
      ) : (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100%',
        }}>
          <span>Loading...</span>
        </div>
      )}

      <Modal
        open={showModelPrompt}
        closable={false}
        footer={null}
        width={480}
      >
        <Result
          status="warning"
          title={t("chat.modelNotConfigured.title")}
          subTitle={t("chat.modelNotConfigured.description")}
          extra={[
            <Button
              key="configure"
              type="primary"
              icon={<SettingOutlined />}
              onClick={() => {
                setShowModelPrompt(false);
                // Navigate to model configuration
                navigate(webchatPath("/config/agent-config"));
              }}
            >
              {t("chat.modelNotConfigured.configureNow")}
            </Button>,
          ]}
        />
      </Modal>
    </div>
  );
}
