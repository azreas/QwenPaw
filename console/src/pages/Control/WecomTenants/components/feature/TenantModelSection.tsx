import { Button, Card, Input } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import type { WecomModelSlot } from "../../../../../api/types";
import styles from "../../index.module.less";

interface Props {
  model: WecomModelSlot;
  loading: boolean;
  saving: boolean;
  onChange: (model: WecomModelSlot) => void;
  onSave: () => Promise<void>;
}

export function TenantModelSection({
  model,
  loading,
  saving,
  onChange,
  onSave,
}: Props) {
  const { t } = useTranslation();

  return (
    <Card title={t("wecomTenants.modelConfig")} loading={loading}>
      <div className={styles.formGrid}>
        <Input
          value={model.provider_id}
          onChange={(event) =>
            onChange({ ...model, provider_id: event.target.value })
          }
          placeholder={t("wecomTenants.providerPlaceholder")}
        />
        <Input
          value={model.model}
          onChange={(event) => onChange({ ...model, model: event.target.value })}
          placeholder={t("wecomTenants.modelPlaceholder")}
        />
        <Button type="primary" loading={saving} onClick={onSave}>
          {t("common.save")}
        </Button>
      </div>
    </Card>
  );
}
