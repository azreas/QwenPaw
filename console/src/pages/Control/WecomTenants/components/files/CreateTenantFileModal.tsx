import { Alert } from "@agentscope-ai/design";
import { Input, Modal } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import styles from "../../index.module.less";

interface Props {
  open: boolean;
  filename: string;
  error: string | null;
  creating: boolean;
  onChange: (value: string) => void;
  onCancel: () => void;
  onCreate: () => Promise<void>;
}

export function CreateTenantFileModal({
  open,
  filename,
  error,
  creating,
  onChange,
  onCancel,
  onCreate,
}: Props) {
  const { t } = useTranslation();

  return (
    <Modal
      title={t("wecomTenants.createFile")}
      open={open}
      okText={t("common.save")}
      cancelText={t("common.cancel")}
      confirmLoading={creating}
      onCancel={onCancel}
      onOk={onCreate}
    >
      {error && (
        <Alert
          className={styles.inlineAlert}
          type="error"
          showIcon
          message={error}
        />
      )}
      <Input
        value={filename}
        onChange={(event) => onChange(event.target.value)}
        placeholder={t("wecomTenants.fileNamePlaceholder")}
      />
      <p className={styles.formHint}>{t("wecomTenants.fileNameHint")}</p>
    </Modal>
  );
}
