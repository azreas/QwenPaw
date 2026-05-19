import { useRef, useState } from "react";
import { Alert } from "@agentscope-ai/design";
import { Button, Card, Input, Modal, Switch } from "@agentscope-ai/design";
import {
  DeleteOutlined,
  DownloadOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type { WecomTenantSummary } from "../../../../api/types";
import { useAppMessage } from "../../../../hooks/useAppMessage";
import styles from "../index.module.less";

interface Props {
  tenant: WecomTenantSummary;
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

export function TenantOperationsTab({ tenant, onDeleted }: Props) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const uploadRef = useRef<HTMLInputElement>(null);
  const [overwrite, setOverwrite] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const exportTenant = async () => {
    setBusyKey("export");
    try {
      const { blob, filename } = await wecomTenantApi.exportWecomTenant(
        tenant.agent_id,
      );
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
      const result = await wecomTenantApi.importWecomTenant(
        tenant.agent_id,
        file,
        overwrite,
      );
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
      content: t("wecomTenants.overwriteImportConfirmContent", {
        agentId: tenant.agent_id,
      }),
      okText: t("wecomTenants.importTenant"),
      cancelText: t("common.cancel"),
      onOk: () => uploadRef.current?.click(),
    });
  };

  const deleteTenant = async () => {
    setBusyKey("delete");
    try {
      await wecomTenantApi.deleteWecomTenant(tenant.agent_id);
      setDeleteOpen(false);
      setDeleteConfirm("");
      message.success(t("wecomTenants.deleteSuccess"));
      await onDeleted();
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className={styles.tabContent}>
      <Alert
        type="warning"
        showIcon
        message={t("wecomTenants.operationsWarning")}
      />

      <Card title={t("wecomTenants.backupRestore")}>
        <div className={styles.operationActions}>
          <Button
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
            icon={<UploadOutlined />}
            loading={busyKey === "import"}
            onClick={chooseImportFile}
          >
            {t("wecomTenants.importTenant")}
          </Button>
          <label className={styles.inlineSwitch}>
            <Switch checked={overwrite} onChange={setOverwrite} />
            <span>{t("wecomTenants.overwriteImport")}</span>
          </label>
        </div>
      </Card>

      <Card title={t("wecomTenants.dangerZone")} className={styles.dangerCard}>
        <p>{t("wecomTenants.deleteTenantDesc")}</p>
        <Button
          danger
          icon={<DeleteOutlined />}
          onClick={() => setDeleteOpen(true)}
        >
          {t("wecomTenants.deleteTenant")}
        </Button>
      </Card>

      <Modal
        title={t("wecomTenants.deleteTenant")}
        open={deleteOpen}
        okText={t("wecomTenants.confirmDelete")}
        okType="danger"
        confirmLoading={busyKey === "delete"}
        okButtonProps={{ disabled: deleteConfirm !== tenant.agent_id }}
        onCancel={() => setDeleteOpen(false)}
        onOk={deleteTenant}
      >
        <Alert
          type="error"
          showIcon
          message={t("wecomTenants.deleteConfirmBody", {
            agentId: tenant.agent_id,
          })}
        />
        <Input
          className={styles.confirmInput}
          value={deleteConfirm}
          onChange={(event) => setDeleteConfirm(event.target.value)}
          placeholder={tenant.agent_id}
        />
      </Modal>
    </div>
  );
}
