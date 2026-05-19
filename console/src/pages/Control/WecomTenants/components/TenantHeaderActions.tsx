import { useRef, useState } from "react";
import { Button, Input, Modal, Switch } from "@agentscope-ai/design";
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  SyncOutlined,
  ReloadOutlined,
  DownloadOutlined,
  UploadOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type { WecomTenantSummary } from "../../../../api/types";
import { useAppMessage } from "../../../../hooks/useAppMessage";
import type { TenantRuntimeAction } from "../hooks/useWecomTenants";
import styles from "../index.module.less";

interface Props {
  tenant: WecomTenantSummary;
  actionKey: string | null;
  onAction: (agentId: string, action: TenantRuntimeAction) => Promise<void>;
  onDeleted: () => Promise<void>;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(link);
}

export function TenantHeaderActions({ tenant, actionKey, onAction, onDeleted }: Props) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const agentId = tenant.agent_id;
  const uploadRef = useRef<HTMLInputElement>(null);
  const [overwrite, setOverwrite] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const exportTenant = async () => {
    setBusyKey("export");
    try {
      const { blob, filename } = await wecomTenantApi.exportWecomTenant(agentId);
      downloadBlob(blob, filename);
      message.success(t("wecomTenants.exportSuccess"));
    } finally {
      setBusyKey(null);
    }
  };

  const importTenant = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusyKey("import");
    try {
      const result = await wecomTenantApi.importWecomTenant(agentId, file, overwrite);
      message.success(result.message || t("wecomTenants.importSuccess"));
    } finally {
      if (uploadRef.current) uploadRef.current.value = "";
      setBusyKey(null);
    }
  };

  const chooseImportFile = () => {
    if (!overwrite) {
      uploadRef.current?.click();
      return;
    }
    Modal.confirm({
      title: t("wecomTenants.overwriteImportConfirmTitle"),
      content: t("wecomTenants.overwriteImportConfirmContent", { agentId }),
      okText: t("wecomTenants.importTenant"),
      cancelText: t("common.cancel"),
      onOk: () => uploadRef.current?.click(),
    });
  };

  const deleteTenant = async () => {
    setBusyKey("delete");
    try {
      await wecomTenantApi.deleteWecomTenant(agentId);
      setDeleteOpen(false);
      setDeleteConfirm("");
      message.success(t("wecomTenants.deleteSuccess"));
      await onDeleted();
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className={styles.headerActionsWrap}>
      {/* 第 1 排：启停操作 */}
      <div className={styles.detailActions}>
        <Button
          size="small"
          icon={<PlayCircleOutlined />}
          disabled={tenant.running || !tenant.exists}
          loading={actionKey === `${agentId}:start`}
          onClick={() => onAction(agentId, "start")}
        >
          {t("wecomTenants.start")}
        </Button>
        <Button
          size="small"
          icon={<PauseCircleOutlined />}
          disabled={!tenant.running}
          loading={actionKey === `${agentId}:stop`}
          onClick={() => onAction(agentId, "stop")}
        >
          {t("wecomTenants.stop")}
        </Button>
        <Button
          size="small"
          icon={<SyncOutlined />}
          disabled={!tenant.exists}
          loading={actionKey === `${agentId}:restart`}
          onClick={() => onAction(agentId, "restart")}
        >
          {t("wecomTenants.restart")}
        </Button>
        <Button
          size="small"
          icon={<ReloadOutlined />}
          disabled={!tenant.running}
          loading={actionKey === `${agentId}:reload`}
          onClick={() => onAction(agentId, "reload")}
        >
          {t("wecomTenants.reload")}
        </Button>
      </div>

      {/* 第 2 排：备份恢复 */}
      <div className={styles.detailActions}>
        <Button
          size="small"
          icon={<DownloadOutlined />}
          loading={busyKey === "export"}
          onClick={exportTenant}
        >
          {t("wecomTenants.exportTenant")}
        </Button>
        <input
          ref={uploadRef}
          type="file"
          accept=".zip"
          className={styles.hiddenInput}
          onChange={importTenant}
        />
        <Button
          size="small"
          icon={<UploadOutlined />}
          loading={busyKey === "import"}
          onClick={chooseImportFile}
        >
          {t("wecomTenants.importTenant")}
        </Button>
        <label className={styles.inlineSwitch}>
          <Switch checked={overwrite} onChange={setOverwrite} size="small" />
          <span>{t("wecomTenants.overwriteImport")}</span>
        </label>
      </div>

      {/* 第 3 排：删除 */}
      <div>
        <Button
          size="small"
          danger
          icon={<DeleteOutlined />}
          onClick={() => setDeleteOpen(true)}
        >
          {t("wecomTenants.deleteTenant")}
        </Button>
      </div>

      {/* 删除确认弹窗 */}
      <Modal
        title={t("wecomTenants.deleteTenant")}
        open={deleteOpen}
        okText={t("wecomTenants.confirmDelete")}
        okType="danger"
        confirmLoading={busyKey === "delete"}
        okButtonProps={{ disabled: deleteConfirm !== agentId }}
        onCancel={() => setDeleteOpen(false)}
        onOk={deleteTenant}
      >
        <p>{t("wecomTenants.deleteConfirmBody", { agentId })}</p>
        <Input
          value={deleteConfirm}
          onChange={(e) => setDeleteConfirm(e.target.value)}
          placeholder={agentId}
        />
      </Modal>
    </div>
  );
}
