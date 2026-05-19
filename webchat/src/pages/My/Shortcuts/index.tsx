import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Card,
  Button,
  Typography,
  Modal,
  Input,
  Form,
  Tag,
  message,
  Popconfirm,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  PictureOutlined,
  FormOutlined,
  TranslationOutlined,
  CodeOutlined,
} from "@ant-design/icons";
import { useTheme } from "../../../contexts/ThemeContext";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

interface Shortcut {
  id: string;
  name: string;
  description: string;
  icon: string;
  prompt: string;
  tags: string[];
}

const mockShortcuts: Shortcut[] = [
  {
    id: "1",
    name: "图片生成",
    description: "根据描述生成高质量图片",
    icon: "image",
    prompt: "请根据以下描述生成一张图片：{description}",
    tags: ["图片", "AI绘图"],
  },
  {
    id: "2",
    name: "标题优化",
    description: "优化文章标题，使其更吸引人",
    icon: "form",
    prompt: "请为以下内容生成5个吸引人的标题：\n{content}",
    tags: ["写作", "优化"],
  },
  {
    id: "3",
    name: "代码审查",
    description: "审查代码并给出优化建议",
    icon: "code",
    prompt: "请审查以下代码并给出优化建议：\n{code}",
    tags: ["编程", "代码质量"],
  },
  {
    id: "4",
    name: "翻译助手",
    description: "将文本翻译为指定语言",
    icon: "translation",
    prompt: "请将以下内容翻译为{language}：\n{text}",
    tags: ["翻译", "多语言"],
  },
];

const getIcon = (iconName: string) => {
  const iconMap: Record<string, JSX.Element> = {
    image: <PictureOutlined style={{ fontSize: 32, color: "#1890ff" }} />,
    form: <FormOutlined style={{ fontSize: 32, color: "#52c41a" }} />,
    code: <CodeOutlined style={{ fontSize: 32, color: "#722ed1" }} />,
    translation: <TranslationOutlined style={{ fontSize: 32, color: "#fa8c16" }} />,
  };
  return iconMap[iconName] || <ThunderboltOutlined style={{ fontSize: 32 }} />;
};

export default function ShortcutsPage() {
  const { t } = useTranslation();
  const { isDark } = useTheme();
  const [shortcuts, setShortcuts] = useState<Shortcut[]>(mockShortcuts);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingShortcut, setEditingShortcut] = useState<Shortcut | null>(null);
  const [form] = Form.useForm();

  const handleCreate = () => {
    setEditingShortcut(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (shortcut: Shortcut) => {
    setEditingShortcut(shortcut);
    form.setFieldsValue(shortcut);
    setModalOpen(true);
  };

  const handleDelete = (id: string) => {
    setShortcuts((prev) => prev.filter((s) => s.id !== id));
    message.success("删除成功");
  };

  const handleSave = async (values: Omit<Shortcut, "id">) => {
    if (editingShortcut) {
      setShortcuts((prev) =>
        prev.map((s) => (s.id === editingShortcut.id ? { ...s, ...values } : s))
      );
      message.success("更新成功");
    } else {
      const newShortcut: Shortcut = {
        ...values,
        id: String(Date.now()),
      };
      setShortcuts((prev) => [...prev, newShortcut]);
      message.success("创建成功");
    }
    setModalOpen(false);
  };

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
        title={t("my.shortcuts")}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            {t("common.create")}
          </Button>
        }
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: 16,
          }}
        >
          {shortcuts.map((shortcut) => (
            <Card
              key={shortcut.id}
              hoverable
              style={{
                background: isDark ? "#2a2a2a" : "#fafafa",
              }}
            >
              <div style={{ marginBottom: 12 }}>
                <div style={{ marginBottom: 12 }}>
                  {getIcon(shortcut.icon)}
                </div>
                <Text strong style={{ fontSize: 16, display: "block", marginBottom: 8 }}>
                  {shortcut.name}
                </Text>
                <Paragraph
                  ellipsis={{ rows: 2 }}
                  style={{ color: isDark ? "#999" : "#666", marginBottom: 12 }}
                >
                  {shortcut.description}
                </Paragraph>
                <div style={{ marginBottom: 12 }}>
                  {shortcut.tags.map((tag) => (
                    <Tag key={tag} style={{ marginRight: 4 }}>
                      {tag}
                    </Tag>
                  ))}
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "flex-end",
                    gap: 8,
                  }}
                >
                  <Button
                    type="text"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => handleEdit(shortcut)}
                  />
                  <Popconfirm
                    title="确定要删除这个快捷指令吗？"
                    onConfirm={() => handleDelete(shortcut.id)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                    />
                  </Popconfirm>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </Card>

      <Modal
        title={editingShortcut ? "编辑快捷指令" : "创建快捷指令"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
        >
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: "请输入名称" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input />
          </Form.Item>
          <Form.Item
            name="prompt"
            label="提示词模板"
            rules={[{ required: true, message: "请输入提示词模板" }]}
          >
            <TextArea rows={6} />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Input placeholder="用逗号分隔多个标签" />
          </Form.Item>
          <Form.Item name="icon" label="图标">
            <Input placeholder="image, form, code, translation" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
