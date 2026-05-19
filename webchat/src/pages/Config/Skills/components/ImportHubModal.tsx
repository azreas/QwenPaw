import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Modal, Button, Input, Alert } from "antd";
import { QuestionCircleOutlined } from "@ant-design/icons";
import styles from "./ImportHubModal.module.less";

const SUPPORTED_SKILL_URL_PREFIXES = [
  "https://github.com/",
  "https://huggingface.co/",
];

function isSupportedSkillUrl(url: string): boolean {
  return SUPPORTED_SKILL_URL_PREFIXES.some((prefix) =>
    url.startsWith(prefix)
  );
}

interface ImportHubModalProps {
  open: boolean;
  importing: boolean;
  onCancel: () => void;
  onConfirm: (url: string, targetName?: string) => Promise<void>;
  cancelImport?: () => void;
  hint?: string;
}

export function ImportHubModal({
  open,
  importing,
  onCancel,
  onConfirm,
  cancelImport,
  hint,
}: ImportHubModalProps) {
  const { t } = useTranslation();
  const [importUrl, setImportUrl] = useState("");
  const [importUrlError, setImportUrlError] = useState("");
  const [targetName, setTargetName] = useState("");

  const handleUrlChange = useCallback((value: string) => {
    setImportUrl(value);
    const trimmed = value.trim();
    if (trimmed && !isSupportedSkillUrl(trimmed)) {
      setImportUrlError(t("skills.invalidSkillUrlSource"));
      return;
    }
    setImportUrlError("");
  }, [t]);

  const handleConfirm = useCallback(async () => {
    const url = importUrl.trim();
    if (!url || importUrlError) return;
    
    await onConfirm(url, targetName.trim() || undefined);
  }, [importUrl, importUrlError, targetName, onConfirm]);

  const handleClose = useCallback(() => {
    if (importing) return;
    setImportUrl("");
    setTargetName("");
    setImportUrlError("");
    onCancel();
  }, [importing, onCancel]);

  return (
    <Modal
      title={t("skills.importHub")}
      open={open}
      width={760}
      onCancel={handleClose}
      footer={
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <Button onClick={handleClose} disabled={importing}>
            {t("common.cancel")}
          </Button>
          <div style={{ display: "flex", gap: 8 }}>
            {cancelImport && importing && (
              <Button danger onClick={cancelImport}>
                {t("common.cancel")}
              </Button>
            )}
            <Button
              type="primary"
              loading={importing}
              disabled={!importUrl.trim() || !!importUrlError}
              onClick={handleConfirm}
            >
              {t("common.import")}
            </Button>
          </div>
        </div>
      }
    >
      <div className={styles.importHintBlock}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <QuestionCircleOutlined />
          <span>{t("skills.supportedSkillUrlSources")}</span>
        </div>
        <ul className={styles.importUrlList}>
          {SUPPORTED_SKILL_URL_PREFIXES.map((url) => (
            <li key={url}>{url}</li>
          ))}
        </ul>
      </div>

      {hint && <Alert message={hint} type="info" style={{ marginBottom: 16 }} />}

      <div style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 8, fontWeight: 500 }}>
          {t("skills.skillUrl")}
        </div>
        <Input
          value={importUrl}
          onChange={(e) => handleUrlChange(e.target.value)}
          placeholder={t("skills.enterSkillUrl")}
          disabled={importing}
          status={importUrlError ? "error" : undefined}
        />
        {importUrlError && (
          <div className={styles.importUrlError}>{importUrlError}</div>
        )}
      </div>

      <div>
        <div style={{ marginBottom: 8, fontWeight: 500 }}>
          {t("skills.targetName")} ({t("common.optional")})
        </div>
        <Input
          value={targetName}
          onChange={(e) => setTargetName(e.target.value)}
          placeholder={t("skills.targetNamePlaceholder")}
          disabled={importing}
        />
      </div>
    </Modal>
  );
}
