import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Space,
  Popconfirm,
  Spin,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  PauseCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useTheme } from "../../../contexts/ThemeContext";
import { useCapabilities } from "../../../contexts/CapabilityContext";
import { tasksApi } from "../../../api/modules/tasks";
import type { WebchatTask } from "../../../api/types/tasks";
import TaskDrawer from "./components/TaskDrawer";

function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  return value.replace("T", " ").replace(/\.\d+Z?$/, "");
}

export default function TasksPage() {
  const { t } = useTranslation();
  const { isDark } = useTheme();
  const { data: capabilityData, loading: capabilityLoading } = useCapabilities();
  const [tasks, setTasks] = useState<WebchatTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<WebchatTask | null>(null);

  const canRunNow =
    !capabilityLoading && capabilityData?.capabilities.task_run_now === true;

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const data = await tasksApi.list();
      setTasks(data);
    } catch (error) {
      console.error("Failed to load tasks:", error);
      message.error(t("tasks.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const stats = useMemo(() => {
    const enabled = tasks.filter((task) => task.enabled).length;
    const disabled = tasks.filter((task) => !task.enabled).length;
    const recentFailed = tasks.filter(
      (task) => task.state?.last_status === "error"
    ).length;
    return {
      total: tasks.length,
      enabled,
      disabled,
      recentFailed,
    };
  }, [tasks]);

  const openCreate = () => {
    setEditingTask(null);
    setDrawerOpen(true);
  };

  const openEdit = (task: WebchatTask) => {
    setEditingTask(task);
    setDrawerOpen(true);
  };

  const handleSave = async (task: WebchatTask) => {
    setSaving(true);
    try {
      if (editingTask?.id) {
        const updated = await tasksApi.update(editingTask.id, task);
        setTasks((prev) =>
          prev.map((item) => (item.id === editingTask.id ? updated : item))
        );
        message.success(t("tasks.updateSuccess"));
      } else {
        const created = await tasksApi.create(task);
        setTasks((prev) => [created, ...prev]);
        message.success(t("tasks.createSuccess"));
      }
      setDrawerOpen(false);
      setEditingTask(null);
    } catch (error) {
      console.error("Failed to save task:", error);
      message.error(t("tasks.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  const runTaskAction = async (
    task: WebchatTask,
    action: "pause" | "resume" | "run" | "remove"
  ) => {
    if (!task.id) {
      message.error(t("tasks.missingId"));
      return;
    }

    setActionLoading(`${action}:${task.id}`);
    try {
      if (action === "pause") {
        await tasksApi.pause(task.id);
        message.success(t("tasks.pauseSuccess"));
      } else if (action === "resume") {
        await tasksApi.resume(task.id);
        message.success(t("tasks.resumeSuccess"));
      } else if (action === "run") {
        await tasksApi.run(task.id);
        message.success(t("tasks.runSuccess"));
      } else {
        await tasksApi.remove(task.id);
        message.success(t("tasks.deleteSuccess"));
      }
      await loadTasks();
    } catch (error) {
      console.error("Failed to operate task:", error);
      message.error(t("tasks.operationFailed"));
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusTag = (task: WebchatTask) => {
    if (!task.enabled) {
      return (
        <Tag color="default" icon={<PauseCircleOutlined />}>
          {t("tasks.statusPaused")}
        </Tag>
      );
    }

    if (task.state?.last_status === "running") {
      return (
        <Tag color="processing" icon={<ClockCircleOutlined />}>
          {t("tasks.statusRunning")}
        </Tag>
      );
    }

    if (task.state?.last_status === "error") {
      return (
        <Tag color="error" icon={<CloseCircleOutlined />}>
          {t("tasks.statusFailed")}
        </Tag>
      );
    }

    return (
      <Tag color="success" icon={<CheckCircleOutlined />}>
        {t("tasks.statusEnabled")}
      </Tag>
    );
  };

  const columns: ColumnsType<WebchatTask> = [
    {
      title: t("tasks.name"),
      dataIndex: "name",
      key: "name",
      ellipsis: true,
    },
    {
      title: t("tasks.status"),
      key: "status",
      render: (_, record) => getStatusTag(record),
    },
    {
      title: t("tasks.schedule"),
      key: "schedule",
      render: (_, record) => record.schedule.cron,
    },
    {
      title: t("tasks.timezone"),
      key: "timezone",
      render: (_, record) => record.schedule.timezone,
    },
    {
      title: t("tasks.lastRun"),
      key: "lastRun",
      render: (_, record) => formatDateTime(record.state?.last_run_at),
    },
    {
      title: t("tasks.nextRun"),
      key: "nextRun",
      render: (_, record) => formatDateTime(record.state?.next_run_at),
    },
    {
      title: t("tasks.actions"),
      key: "action",
      width: 260,
      render: (_, record) => {
        const taskId = record.id || "";
        return (
          <Space size={4} wrap>
            <Button type="link" size="small" onClick={() => openEdit(record)}>
              {t("common.edit")}
            </Button>
            {record.enabled ? (
              <Button
                type="link"
                size="small"
                loading={actionLoading === `pause:${taskId}`}
                onClick={() => runTaskAction(record, "pause")}
              >
                {t("tasks.pause")}
              </Button>
            ) : (
              <Button
                type="link"
                size="small"
                loading={actionLoading === `resume:${taskId}`}
                onClick={() => runTaskAction(record, "resume")}
              >
                {t("tasks.resume")}
              </Button>
            )}
            {canRunNow && (
              <Button
                type="link"
                size="small"
                loading={actionLoading === `run:${taskId}`}
                onClick={() => runTaskAction(record, "run")}
              >
                {t("tasks.runNow")}
              </Button>
            )}
            <Popconfirm
              title={t("tasks.deleteConfirm")}
              okText={t("common.confirm")}
              cancelText={t("common.cancel")}
              onConfirm={() => runTaskAction(record, "remove")}
            >
              <Button
                type="link"
                size="small"
                danger
                loading={actionLoading === `remove:${taskId}`}
              >
                {t("common.delete")}
              </Button>
            </Popconfirm>
          </Space>
        );
      },
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
        title={t("my.tasks")}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadTasks} loading={loading}>
              {t("common.refresh")}
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              {t("tasks.createTask")}
            </Button>
          </Space>
        }
      >
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title={t("tasks.totalTasks")}
                value={stats.total}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title={t("tasks.enabledTasks")}
                value={stats.enabled}
                valueStyle={{ color: "#52c41a" }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title={t("tasks.disabledTasks")}
                value={stats.disabled}
                prefix={<PauseCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title={t("tasks.recentFailed")}
                value={stats.recentFailed}
                valueStyle={{ color: stats.recentFailed > 0 ? "#ff4d4f" : undefined }}
                prefix={<CloseCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <Spin spinning={loading}>
          <Table<WebchatTask>
            columns={columns}
            dataSource={tasks}
            rowKey={(record) => record.id || record.name}
            pagination={{ pageSize: 10 }}
          />
        </Spin>
      </Card>

      <TaskDrawer
        open={drawerOpen}
        task={editingTask}
        saving={saving}
        onClose={() => {
          setDrawerOpen(false);
          setEditingTask(null);
        }}
        onSubmit={handleSave}
      />
    </div>
  );
}
