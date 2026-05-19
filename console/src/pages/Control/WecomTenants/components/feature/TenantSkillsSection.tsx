import { useMemo, useState } from "react";
import { Button, Card, Input, Modal, Switch, Table, Tag, Tooltip } from "@agentscope-ai/design";
import type { ColumnsType } from "antd/es/table";
import { useTranslation } from "react-i18next";
import { skillApi } from "../../../../../api/modules/skill";
import { wecomTenantApi } from "../../../../../api/modules/wecomTenant";
import type { PoolSkillSpec, WecomTenantSkill } from "../../../../../api/types";
import { useAppMessage } from "../../../../../hooks/useAppMessage";
import styles from "../../index.module.less";

interface Props {
  agentId: string;
  skills: WecomTenantSkill[];
  loading: boolean;
  onRefresh: () => Promise<void>;
}

function textIncludes(value: string | undefined, query: string) {
  return (value || "").toLowerCase().includes(query);
}

export function TenantSkillsSection({
  agentId,
  skills,
  loading,
  onRefresh,
}: Props) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [poolOpen, setPoolOpen] = useState(false);
  const [poolSkills, setPoolSkills] = useState<PoolSkillSpec[]>([]);
  const [poolLoading, setPoolLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [overwrite, setOverwrite] = useState(false);
  const [savingSkill, setSavingSkill] = useState<string | null>(null);

  const installedNames = useMemo(
    () =>
      new Set(
        skills
          .filter((skill) => skill.installed !== false)
          .map((skill) => skill.name),
      ),
    [skills],
  );

  const filteredPoolSkills = useMemo(() => {
    const text = query.trim().toLowerCase();
    if (!text) return poolSkills;
    return poolSkills.filter((skill) => {
      const tagText = (skill.tags || []).join(" ");
      return (
        textIncludes(skill.name, text) ||
        textIncludes(skill.description, text) ||
        textIncludes(tagText, text)
      );
    });
  }, [poolSkills, query]);

  const loadPool = async () => {
    setPoolLoading(true);
    try {
      setPoolSkills(await skillApi.listSkillPoolSkills());
    } catch (error) {
      message.error((error as Error).message || t("wecomTenants.loadFailed"));
    } finally {
      setPoolLoading(false);
    }
  };

  const openPool = async () => {
    setPoolOpen(true);
    if (!poolSkills.length) {
      await loadPool();
    }
  };

  const installSkill = async (skillName: string, forceOverwrite = overwrite) => {
    setSavingSkill(skillName);
    try {
      await wecomTenantApi.installWecomTenantSkill(agentId, {
        skill_id: skillName,
        overwrite: forceOverwrite,
      });
      message.success(t("wecomTenants.skillInstallSuccess", { name: skillName }));
      await onRefresh();
    } finally {
      setSavingSkill(null);
    }
  };

  const confirmInstall = (skill: PoolSkillSpec) => {
    const installed = installedNames.has(skill.name);
    if (installed && !overwrite) return;
    if (!overwrite) {
      installSkill(skill.name);
      return;
    }
    Modal.confirm({
      title: t("wecomTenants.skillOverwriteConfirmTitle"),
      content: t("wecomTenants.skillOverwriteConfirmContent", {
        name: skill.name,
        agentId,
      }),
      okText: t("wecomTenants.installSkill"),
      cancelText: t("common.cancel"),
      onOk: () => installSkill(skill.name, true),
    });
  };

  const deleteSkill = (skill: WecomTenantSkill) => {
    Modal.confirm({
      title: t("wecomTenants.deleteSkillTitle", { name: skill.name }),
      content: t("wecomTenants.deleteSkillContent", {
        name: skill.name,
        agentId,
      }),
      okText: t("common.delete"),
      okType: "danger",
      cancelText: t("common.cancel"),
      onOk: async () => {
        await wecomTenantApi.deleteWecomTenantSkill(agentId, skill.name);
        message.success(t("wecomTenants.skillDeleteSuccess", { name: skill.name }));
        await onRefresh();
      },
    });
  };

  const skillColumns: ColumnsType<WecomTenantSkill> = [
    {
      title: t("wecomTenants.name"),
      dataIndex: "name",
      key: "name",
      render: (value: string, skill) => (
        <div className={styles.tenantIdentity}>
          <strong>{value}</strong>
          <span>
            {skill.installed === false
              ? `${t("wecomTenants.skillPendingInstall")} · ${
                  skill.description || "-"
                }`
              : skill.description || "-"}
          </span>
        </div>
      ),
    },
    {
      title: t("wecomTenants.source"),
      dataIndex: "source",
      key: "source",
      width: 110,
      render: (value: string, skill) =>
        skill.installed === false ? (
          <Tag>{t("wecomTenants.uploadedMediaSkill")}</Tag>
        ) : (
          value
        ),
    },
    {
      title: t("wecomTenants.skillChannels"),
      key: "channels",
      render: (_, skill) => (
        <div className={styles.rowActions}>
          {(skill.installed === false
            ? [t("wecomTenants.skillPendingInstall")]
            : skill.channels?.length
              ? skill.channels
              : ["all"]
          ).map((channel) => (
            <Tag key={channel}>{channel}</Tag>
          ))}
        </div>
      ),
    },
    {
      title: t("wecomTenants.enabled"),
      key: "enabled",
      width: 90,
      render: (_, skill) => (
        <Switch
          checked={skill.enabled}
          disabled={skill.installed === false}
          onChange={async () => {
            await wecomTenantApi.toggleWecomTenantSkill(agentId, skill.name);
            await onRefresh();
          }}
        />
      ),
    },
    {
      title: t("wecomTenants.lastCall"),
      key: "last_call",
      width: 120,
      render: (_, skill) => {
        if (!skill.last_call_status) return <Tag>-</Tag>;
        const color = skill.last_call_status === "success" ? "green" : "red";
        const tip = skill.last_error_reason || "";
        return (
          <Tooltip title={tip}>
            <Tag color={color}>{skill.last_call_status}</Tag>
          </Tooltip>
        );
      },
    },
    {
      title: t("wecomTenants.actions"),
      key: "actions",
      width: 120,
      render: (_, skill) => {
        if (skill.installed === false && skill.installable) {
          return (
            <Button
              size="small"
              type="primary"
              loading={savingSkill === skill.name}
              onClick={() => installSkill(skill.name, overwrite)}
            >
              {t("wecomTenants.importUploadedSkill")}
            </Button>
          );
        }
        return (
          <Button size="small" danger onClick={() => deleteSkill(skill)}>
            {t("common.delete")}
          </Button>
        );
      },
    },
  ];

  const poolColumns: ColumnsType<PoolSkillSpec> = [
    {
      title: t("wecomTenants.name"),
      dataIndex: "name",
      key: "name",
      render: (value: string, skill) => (
        <div className={styles.tenantIdentity}>
          <strong>{value}</strong>
          <span>{skill.description || "-"}</span>
        </div>
      ),
    },
    {
      title: t("wecomTenants.source"),
      dataIndex: "source",
      key: "source",
      width: 120,
    },
    {
      title: t("wecomTenants.skillTags"),
      key: "tags",
      render: (_, skill) => (
        <div className={styles.rowActions}>
          {(skill.tags || []).slice(0, 3).map((tag) => (
            <Tag key={tag}>{tag}</Tag>
          ))}
        </div>
      ),
    },
    {
      title: t("wecomTenants.actions"),
      key: "actions",
      width: 120,
      render: (_, skill) => {
        const installed = installedNames.has(skill.name);
        const disabled = installed && !overwrite;
        const button = (
          <Button
            size="small"
            type={installed ? "default" : "primary"}
            disabled={disabled}
            loading={savingSkill === skill.name}
            onClick={() => confirmInstall(skill)}
          >
            {installed
              ? t("wecomTenants.skillInstalled")
              : t("wecomTenants.installSkill")}
          </Button>
        );
        return disabled ? (
          <Tooltip title={t("wecomTenants.enableOverwriteToInstall")}>
            {button}
          </Tooltip>
        ) : (
          button
        );
      },
    },
  ];

  return (
    <Card
      title={t("wecomTenants.skills")}
      bodyStyle={{ padding: 0 }}
      extra={<Button onClick={openPool}>{t("wecomTenants.installFromPool")}</Button>}
    >
      <Table
        columns={skillColumns}
        dataSource={skills}
        rowKey="name"
        loading={loading}
        pagination={false}
        size="small"
        scroll={{ x: 760 }}
      />

      <Modal
        title={t("wecomTenants.installFromPool")}
        open={poolOpen}
        width={860}
        footer={null}
        onCancel={() => setPoolOpen(false)}
      >
        <div className={styles.tableToolbar}>
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("wecomTenants.skillPoolSearchPlaceholder")}
          />
          <Button onClick={loadPool} loading={poolLoading}>
            {t("common.refresh")}
          </Button>
          <label className={styles.inlineSwitch}>
            <Switch checked={overwrite} onChange={setOverwrite} />
            <span>{t("wecomTenants.overwriteInstalledSkill")}</span>
          </label>
        </div>
        <Table<PoolSkillSpec>
          columns={poolColumns}
          dataSource={filteredPoolSkills}
          rowKey="name"
          loading={poolLoading}
          size="small"
          pagination={{ pageSize: 8, showSizeChanger: false }}
          scroll={{ x: 780 }}
        />
      </Modal>
    </Card>
  );
}
