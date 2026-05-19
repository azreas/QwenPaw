import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Card,
  List,
  Avatar,
  Badge,
  Tabs,
  Button,
  Typography,
} from "antd";
import {
  MessageOutlined,
  BellOutlined,
  MailOutlined,
  ReadOutlined,
} from "@ant-design/icons";
import { useTheme } from "../../../contexts/ThemeContext";

const { Text, Paragraph } = Typography;

interface Message {
  id: string;
  type: "system" | "user" | "notification";
  title: string;
  content: string;
  time: string;
  read: boolean;
  avatar?: string;
}

const mockMessages: Message[] = [
  {
    id: "1",
    type: "system",
    title: "系统通知",
    content: "您的任务「数据预处理」已完成，请查看结果。",
    time: "2026-04-14 11:30:00",
    read: false,
  },
  {
    id: "2",
    type: "user",
    title: "张三",
    content: "你好，请问模型训练的进度如何了？",
    time: "2026-04-14 10:15:00",
    read: false,
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=user1",
  },
  {
    id: "3",
    type: "notification",
    title: "技能更新",
    content: "新的技能「图像生成」已上线，欢迎体验。",
    time: "2026-04-14 09:00:00",
    read: true,
  },
  {
    id: "4",
    type: "system",
    title: "系统维护",
    content: "系统将于今晚22:00-23:00进行例行维护，请提前保存工作。",
    time: "2026-04-13 16:00:00",
    read: true,
  },
  {
    id: "5",
    type: "user",
    title: "李四",
    content: "报表生成的需求已经确认，请尽快处理。",
    time: "2026-04-13 14:20:00",
    read: true,
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=user2",
  },
];

export default function MessagesPage() {
  const { t } = useTranslation();
  const { isDark } = useTheme();
  const [messages, setMessages] = useState<Message[]>(mockMessages);
  const [activeTab, setActiveTab] = useState<string>("all");

  const unreadCount = messages.filter((m) => !m.read).length;

  const filteredMessages =
    activeTab === "all"
      ? messages
      : messages.filter((m) => m.type === activeTab);

  const handleMarkAsRead = (id: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, read: true } : m))
    );
  };

  const handleMarkAllAsRead = () => {
    setMessages((prev) => prev.map((m) => ({ ...m, read: true })));
  };

  const getAvatar = (message: Message) => {
    if (message.type === "system") {
      return <Avatar icon={<BellOutlined />} style={{ backgroundColor: "#1890ff" }} />;
    }
    if (message.type === "notification") {
      return <Avatar icon={<MailOutlined />} style={{ backgroundColor: "#52c41a" }} />;
    }
    return message.avatar ? (
      <Avatar src={message.avatar} />
    ) : (
      <Avatar icon={<MessageOutlined />} />
    );
  };

  const items = [
    {
      key: "all",
      label: `全部消息 (${messages.length})`,
    },
    {
      key: "system",
      label: "系统通知",
    },
    {
      key: "user",
      label: "用户消息",
    },
    {
      key: "notification",
      label: "通知",
    },
  ];

  return (
    <div style={{ padding: "24px", height: "100%", overflow: "auto" }}>
      <Card
        style={{
          background: isDark ? "#1f1f1f" : "#fff",
          borderColor: isDark ? "#303030" : "#f0f0f0",
        }}
        styles={{
          header: {
            padding: "16px 24px",
            borderBottom: `1px solid ${isDark ? "rgba(255,255,255,0.08)" : "#f0f0f0"}`,
          },
          body: { padding: "24px" },
        }}
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <ReadOutlined />
            <span>{t("my.messages")}</span>
            {unreadCount > 0 && (
              <Badge count={unreadCount} style={{ marginLeft: 8 }} />
            )}
          </div>
        }
        extra={
          unreadCount > 0 && (
            <Button type="link" onClick={handleMarkAllAsRead}>
              全部标为已读
            </Button>
          )
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={items} />

        <List
          dataSource={filteredMessages}
          renderItem={(message) => (
            <List.Item
              onClick={() => handleMarkAsRead(message.id)}
              style={{
                cursor: "pointer",
                background: message.read ? "transparent" : isDark ? "#2a2a2a" : "#f0f5ff",
                padding: "12px 16px",
                borderRadius: 8,
                marginBottom: 8,
              }}
            >
              <List.Item.Meta
                avatar={
                  <Badge dot={!message.read}>
                    {getAvatar(message)}
                  </Badge>
                }
                title={
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <Text strong={!message.read}>{message.title}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {message.time}
                    </Text>
                  </div>
                }
                description={
                  <Paragraph
                    ellipsis={{ rows: 2 }}
                    style={{ margin: "8px 0 0 0", color: isDark ? "#999" : "#666" }}
                  >
                    {message.content}
                  </Paragraph>
                }
              />
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
}
