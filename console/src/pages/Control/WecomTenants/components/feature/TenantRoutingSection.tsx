import { useTranslation } from "react-i18next";
import type { WecomLlmRoutingConfig } from "../../../../../api/types";
import { TenantJsonEditorCard } from "./TenantJsonEditorCard";

interface Props {
  value: string;
  loading: boolean;
  saving: boolean;
  onChange: (value: string) => void;
  onSave: (value: WecomLlmRoutingConfig) => Promise<void>;
}

export function TenantRoutingSection({
  value,
  loading,
  saving,
  onChange,
  onSave,
}: Props) {
  const { t } = useTranslation();

  return (
    <TenantJsonEditorCard<WecomLlmRoutingConfig>
      title={t("wecomTenants.llmRouting")}
      value={value}
      loading={loading}
      saving={saving}
      onChange={onChange}
      onSave={onSave}
    />
  );
}
