import { IAgentScopeRuntimeWebUIOptions } from "@agentscope-ai/chat";

export const defaultConfig: IAgentScopeRuntimeWebUIOptions = {
  theme: {
    colorPrimary: "#FF7F16",
    darkMode: false,
    prefix: "xiaoxuan",
    leftHeader: {
      logo: "",
      title: "小轩",
    },
  },
  sender: {
    attachments: {
      trigger: undefined,
      customRequest: undefined,
    },
    maxLength: 10000,
    disclaimer: "与你同行，伴你成长",
  },
  welcome: {
    greeting: "你好，今天我能帮你什么？",
    description: "我是一个智能助手，可以帮助你解答问题。",
    avatar:
      "https://gw.alicdn.com/imgextra/i2/O1CN01pyXzjQ1EL1PuZMlSd_!!6000000000334-2-tps-288-288.png",
    prompts: [
      { value: "让我们开始一段新的旅程！" },
      { value: "你能告诉我你有什么技能吗？" },
    ],
  },
  session: {
    multiple: true,
  },
  api: {
    baseURL: "",
    token: "",
  },
} as const;

export function getDefaultConfig(t: (key: string) => string) {
  return {
    ...defaultConfig,
    sender: {
      ...defaultConfig.sender,
      disclaimer: t("chat.disclaimer"),
    },
    welcome: {
      ...defaultConfig.welcome,
      greeting: t("chat.greeting"),
      description: t("chat.description"),
      prompts: [{ value: t("chat.prompt1") }, { value: t("chat.prompt2") }],
    },
  };
}