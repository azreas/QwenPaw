import { Button, Card, Input } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import styles from "../../index.module.less";

interface Props {
  value: string;
  loading: boolean;
  saving: boolean;
  onChange: (value: string) => void;
  onSave: () => Promise<void>;
}

export function TenantSystemPromptsSection({
  value,
  loading,
  saving,
  onChange,
  onSave,
}: Props) {
  const { t } = useTranslation();

  return (
    <Card title={t("wecomTenants.systemPrompts")} loading={loading}>
      <Input.TextArea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoSize={{ minRows: 6, maxRows: 10 }}
        placeholder="AGENTS.md&#10;SOUL.md"
      />
      <Button
        type="primary"
        className={styles.sectionButton}
        loading={saving}
        onClick={onSave}
      >
        {t("common.save")}
      </Button>
    </Card>
  );
}
