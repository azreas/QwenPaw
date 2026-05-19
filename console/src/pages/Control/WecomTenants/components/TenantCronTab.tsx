import { useEffect, useMemo, useState } from "react";
import { Empty } from "@agentscope-ai/design";
import {
  Button,
  Card,
  Form,
  Modal,
  Table,
  Tag,
  Tooltip,
} from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type {
  WecomTenantCronJob,
  WecomTenantCronJobInput,
} from "../../../../api/types";
import { useAppMessage } from "../../../../hooks/useAppMessage";
import styles from "../index.module.less";
import { TenantCronJobModal } from "./cron/TenantCronJobModal";
import {
  DEFAULT_JOB,
  type CronFormValues,
  formatRuntimeTime,
  jobRuntimeValue,
  jobToForm,
  readableError,
  valuesToPayload,
} from "./cron/tenantCronForm";

interface Props {
  agentId: string;
  running: boolean;
}

export function TenantCronTab({ agentId, running }: Props) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [jobs, setJobs] = useState<WecomTenantCronJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingJobId, setEditingJobId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form] = Form.useForm<CronFormValues>();

  const load = async () => {
    setLoading(true);
    try {
      setJobs(await wecomTenantApi.listWecomTenantCronJobs(agentId));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]);

  const openCreate = () => {
    setEditingJobId(null);
    setFormError(null);
    form.setFieldsValue(DEFAULT_JOB);
    setModalOpen(true);
  };

  const openEdit = (job: WecomTenantCronJob) => {
    setEditingJobId(job.id);
    setFormError(null);
    form.setFieldsValue(jobToForm(job));
    setModalOpen(true);
  };

  const saveJob = async () => {
    const values = await form.validateFields();
    let parsed: WecomTenantCronJobInput;
    try {
      parsed = valuesToPayload(values);
      if (editingJobId) parsed.id = editingJobId;
      setFormError(null);
    } catch (error) {
      setFormError(readableError(error));
      return;
    }

    setSaving(true);
    try {
      if (editingJobId) {
        await wecomTenantApi.updateWecomTenantCronJob(agentId, editingJobId, parsed);
      } else {
        await wecomTenantApi.createWecomTenantCronJob(agentId, parsed);
      }
      setModalOpen(false);
      message.success(t("wecomTenants.saved"));
      await load();
    } catch (error) {
      setFormError(readableError(error));
    } finally {
      setSaving(false);
    }
  };

  const runNow = async (job: WecomTenantCronJob) => {
    try {
      await wecomTenantApi.runWecomTenantCronJob(agentId, job.id);
      message.success(t("wecomTenants.actionSuccess"));
    } catch (error) {
      message.error(readableError(error));
    }
  };

  const deleteJob = (job: WecomTenantCronJob) => {
    Modal.confirm({
      title: t("wecomTenants.deleteCronTitle"),
      content: t("wecomTenants.deleteCronContent", { name: job.name }),
      okText: t("common.delete"),
      okType: "danger",
      cancelText: t("common.cancel"),
      onOk: async () => {
        await wecomTenantApi.deleteWecomTenantCronJob(agentId, job.id);
        await load();
      },
    });
  };

  const columns: ColumnsType<WecomTenantCronJob> = useMemo(
    () => [
      { title: t("wecomTenants.name"), dataIndex: "name", key: "name" },
      {
        title: t("wecomTenants.enabled"),
        dataIndex: "enabled",
        key: "enabled",
        render: (enabled: boolean) => (
          <Tag color={enabled ? "green" : "default"}>
            {enabled ? t("common.enabled") : t("common.disabled")}
          </Tag>
        ),
      },
      {
        title: t("wecomTenants.cron"),
        key: "cron",
        render: (_, job) => (
          <code>
            {job.schedule?.type === "cron" ? job.schedule.cron : "-"}
          </code>
        ),
      },
      {
        title: t("wecomTenants.timezone"),
        key: "timezone",
        render: (_, job) => job.schedule?.timezone || "-",
      },
      {
        title: t("wecomTenants.nextRun"),
        key: "nextRun",
        render: (_, job) => formatRuntimeTime(jobRuntimeValue(job, "next_run_at")),
      },
      {
        title: t("wecomTenants.lastRun"),
        key: "lastRun",
        render: (_, job) => formatRuntimeTime(jobRuntimeValue(job, "last_run_at")),
      },
      {
        title: t("wecomTenants.actions"),
        key: "actions",
        render: (_, job) => (
          <div className={styles.rowActions}>
            <Button size="small" onClick={() => openEdit(job)}>
              {t("common.edit")}
            </Button>
            <Tooltip title={!running ? t("wecomTenants.runNowDisabled") : undefined}>
              <span>
                <Button
                  size="small"
                  disabled={!running}
                  onClick={() => runNow(job)}
                >
                  {t("wecomTenants.runNow")}
                </Button>
              </span>
            </Tooltip>
            <Button
              size="small"
              onClick={async () => {
                if (job.enabled) {
                  await wecomTenantApi.pauseWecomTenantCronJob(agentId, job.id);
                } else {
                  await wecomTenantApi.resumeWecomTenantCronJob(agentId, job.id);
                }
                await load();
              }}
            >
              {job.enabled ? t("wecomTenants.pause") : t("wecomTenants.resume")}
            </Button>
            <Button
              size="small"
              danger
              onClick={() => deleteJob(job)}
            >
              {t("common.delete")}
            </Button>
          </div>
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [agentId, running, t],
  );

  return (
    <div className={styles.tabContent}>
      <Card
        title={t("wecomTenants.cronJobs")}
        bodyStyle={{ padding: 0 }}
        extra={<Button onClick={openCreate}>{t("wecomTenants.createJob")}</Button>}
      >
        {jobs.length || loading ? (
          <Table
            columns={columns}
            dataSource={jobs}
            rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          scroll={{ x: 1160 }}
        />
      ) : (
          <Empty description={t("wecomTenants.noCronJobs")} />
        )}
      </Card>
      <TenantCronJobModal
        open={modalOpen}
        editing={!!editingJobId}
        saving={saving}
        error={formError}
        form={form}
        onCancel={() => setModalOpen(false)}
        onSave={saveJob}
      />
    </div>
  );
}
