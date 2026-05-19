import { useState } from "react";
import { Alert } from "@agentscope-ai/design";
import { Button, Card, Input, Modal } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import { useAppMessage } from "../../../../../hooks/useAppMessage";
import styles from "../../index.module.less";

interface Props<TValue> {
  title: string;
  value: string;
  loading?: boolean;
  saving?: boolean;
  minRows?: number;
  onChange: (value: string) => void;
  onSave: (value: TValue) => Promise<void>;
}

function parseJson<TValue>(raw: string): TValue {
  return JSON.parse(raw) as TValue;
}

export function TenantJsonEditorCard<TValue>({
  title,
  value,
  loading,
  saving,
  minRows = 8,
  onChange,
  onSave,
}: Props<TValue>) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [error, setError] = useState<string | null>(null);

  const formatJson = () => {
    try {
      const parsed = parseJson<unknown>(value);
      onChange(JSON.stringify(parsed, null, 2));
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const save = () => {
    let parsed: TValue;
    try {
      parsed = parseJson<TValue>(value);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
      return;
    }

    Modal.confirm({
      title: t("wecomTenants.jsonOverwriteConfirmTitle"),
      content: t("wecomTenants.jsonOverwriteConfirmContent"),
      okText: t("common.save"),
      cancelText: t("common.cancel"),
      onOk: async () => {
        await onSave(parsed);
        message.success(t("wecomTenants.configSavedReloaded"));
      },
    });
  };

  return (
    <Card title={title} loading={loading}>
      {error && (
        <Alert
          className={styles.inlineAlert}
          type="error"
          showIcon
          message={t("wecomTenants.jsonInvalid")}
          description={error}
        />
      )}
      <Input.TextArea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoSize={{ minRows, maxRows: 14 }}
      />
      <div className={styles.formActions}>
        <Button onClick={formatJson}>{t("wecomTenants.formatJson")}</Button>
        <Button type="primary" loading={saving} onClick={save}>
          {t("common.save")}
        </Button>
      </div>
    </Card>
  );
}
