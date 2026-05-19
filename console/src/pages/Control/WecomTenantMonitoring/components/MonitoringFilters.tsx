import { Button, Input, Select } from "@agentscope-ai/design";
import { DatePicker } from "antd";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import type { MonitoringFilters } from "../model";

const { RangePicker } = DatePicker;

interface Props {
  filters: MonitoringFilters;
  onChange: (filters: MonitoringFilters) => void;
  onRefresh: () => void;
  loading: boolean;
}

export function MonitoringFilters({
  filters,
  onChange,
  onRefresh,
  loading,
}: Props) {
  const { t } = useTranslation();

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
      <RangePicker
        value={
          filters.dateRange
            ? [dayjs(filters.dateRange[0]), dayjs(filters.dateRange[1])]
            : undefined
        }
        onChange={(dates) => {
          onChange({
            ...filters,
            dateRange: dates
              ? [dates[0]!.format("YYYY-MM-DD"), dates[1]!.format("YYYY-MM-DD")]
              : undefined,
          });
        }}
      />
      <Select
        value={filters.status ?? "all"}
        onChange={(value: string) =>
          onChange({ ...filters, status: value as MonitoringFilters["status"] })
        }
        style={{ minWidth: 120 }}
      >
        <Select.Option value="all">{t("wecomTenantMonitoring.all")}</Select.Option>
        <Select.Option value="running">{t("wecomTenantMonitoring.running")}</Select.Option>
        <Select.Option value="stopped">{t("wecomTenantMonitoring.stopped")}</Select.Option>
      </Select>
      <Select
        value={filters.health ?? "all"}
        onChange={(value: string) =>
          onChange({ ...filters, health: value as MonitoringFilters["health"] })
        }
        style={{ minWidth: 120 }}
      >
        <Select.Option value="all">{t("wecomTenantMonitoring.all")}</Select.Option>
        <Select.Option value="healthy">{t("wecomTenantMonitoring.healthy")}</Select.Option>
        <Select.Option value="degraded">{t("wecomTenantMonitoring.degraded")}</Select.Option>
        <Select.Option value="unhealthy">{t("wecomTenantMonitoring.unhealthy")}</Select.Option>
      </Select>
      <Input
        placeholder={t("wecomTenantMonitoring.searchPlaceholder")}
        value={filters.search ?? ""}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
          onChange({ ...filters, search: e.target.value || undefined })
        }
        style={{ maxWidth: 260 }}
        allowClear
      />
      <Button type="primary" loading={loading} onClick={onRefresh}>
        {t("wecomTenantMonitoring.refresh")}
      </Button>
    </div>
  );
}
