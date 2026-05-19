export interface CopyableResponse {
  cards?: Array<{
    data?: {
      output?: Array<{
        content?: unknown;
      }>;
    };
  }>;
}

export interface RuntimeLoadingBridgeApi {
  show: (() => void) | null;
  hide: (() => void) | null;
}

export function extractCopyableText(response: CopyableResponse): string {
  const output = response?.cards?.[0]?.data?.output || [];
  return output
    .map((msg) => {
      const content = msg.content;
      if (typeof content === "string") return content;
      if (Array.isArray(content)) {
        return content
          .filter((c: { type?: string }) => c.type === "text")
          .map((c: { text?: string }) => c.text || "")
          .join("\n");
      }
      return "";
    })
    .join("\n");
}

export async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch (err) {
    console.error("Failed to copy text: ", err);
    // Fallback to execCommand if clipboard API fails
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      const successful = document.execCommand("copy");
      if (!successful) {
        throw new Error("ExecCommand failed");
      }
    } catch (error) {
      console.error("Fallback copy method failed: ", error);
    }
    document.body.removeChild(textArea);
  }
}

export function toDisplayUrl(url: string): string {
  // In a real implementation, this would transform URLs for display
  // For now, we'll just return the URL as-is
  return url;
}

export function normalizeContentUrls(content: any[]): any[] {
  // In a real implementation, this would normalize URLs in content
  // For now, we'll just return the content as-is
  return content;
}

export function extractUserMessageText(msg: any): string {
  if (!msg?.content) return "";
  
  if (typeof msg.content === "string") {
    return msg.content.trim();
  }
  
  if (Array.isArray(msg.content)) {
    return msg.content
      .filter((item: any) => item.type === "text")
      .map((item: any) => item.text || "")
      .join(" ")
      .trim();
  }
  
  // 处理对象类型的 content
  if (typeof msg.content === "object" && msg.content !== null) {
    if (msg.content.hasOwnProperty("text")) {
      return String(msg.content.text || "").trim();
    } else if (msg.content.hasOwnProperty("content")) {
      return String(msg.content.content || "").trim();
    } else {
      try {
        return JSON.stringify(msg.content);
      } catch (e) {
        return String(msg.content);
      }
    }
  }
  
  return "";
}

export function extractTextFromMessage(msg: any): string {
  if (!msg) return "";
  
  if (typeof msg === "string") {
    return msg;
  }
  
  if (msg.text) {
    return msg.text;
  }
  
  if (msg.content) {
    if (typeof msg.content === "string") {
      return msg.content;
    }
    if (Array.isArray(msg.content)) {
      return msg.content
        .map((item: any) => item.text || "")
        .filter(Boolean)
        .join(" ");
    }
    // 处理对象类型的 content
    if (typeof msg.content === "object" && msg.content !== null) {
      if (msg.content.hasOwnProperty("text")) {
        return String(msg.content.text || "");
      } else if (msg.content.hasOwnProperty("content")) {
        return String(msg.content.content || "");
      } else {
        try {
          return JSON.stringify(msg.content);
        } catch (e) {
          return String(msg.content);
        }
      }
    }
  }
  
  // 处理 msg 本身是对象但没有 text 或 content 属性的情况
  if (typeof msg === "object" && msg !== null) {
    if (msg.hasOwnProperty("text")) {
      return String(msg.text || "");
    } else if (msg.hasOwnProperty("content")) {
      return extractTextFromMessage(msg.content);
    } else {
      try {
        return JSON.stringify(msg);
      } catch (e) {
        return String(msg);
      }
    }
  }
  
  return "";
}

export function setTextareaValue(value: string): void {
  // In a real implementation, this would set the value of the textarea
  // Since we can't directly access the AgentScopeRuntimeWebUI internals,
  // we'll just log this for now
  console.log("Would set textarea value to:", value);
}

export function buildModelError(): Response {
  // Create a mock response for when model is not configured
  const errorResponse = {
    ok: false,
    status: 500,
    json: async () => ({ error: "Model not configured" }),
    text: async () => "Model not configured",
  } as Response;
  
  return errorResponse;
}