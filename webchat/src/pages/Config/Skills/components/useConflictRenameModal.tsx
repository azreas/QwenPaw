import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Modal, Input, Button } from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";

export interface ConflictItem {
  key: string;
  label: string;
  suggested_name: string;
}

interface InternalItem extends ConflictItem {
  new_name: string;
}

export function useConflictRenameModal(): {
  showConflictRenameModal: (
    items: ConflictItem[],
  ) => Promise<Record<string, string> | null>;
  conflictRenameModal: React.ReactNode;
} {
  const { t } = useTranslation();
  const [items, setItems] = useState<InternalItem[]>([]);
  const [resolver, setResolver] = useState<
    ((result: Record<string, string> | null) => void) | null
  >(null);

  const showConflictRenameModal = useCallback(
    (
      incoming: ConflictItem[],
    ): Promise<Record<string, string> | null> =>
      new Promise((resolve) => {
        setItems(
          incoming.map((item) => ({ ...item, new_name: item.suggested_name })),
        );
        setResolver(() => resolve);
      }),
    [],
  );

  const handleCancel = useCallback(() => {
    if (resolver) {
      resolver(null);
      setResolver(null);
      setItems([]);
    }
  }, [resolver]);

  const handleOk = useCallback(() => {
    if (resolver) {
      const result: Record<string, string> = {};
      items.forEach((item) => {
        result[item.key] = item.new_name;
      });
      resolver(result);
      setResolver(null);
      setItems([]);
    }
  }, [resolver, items]);

  const handleAddRename = useCallback(() => {
    setItems([
      ...items,
      {
        key: `custom_${Date.now()}`,
        label: `New Skill`,
        suggested_name: `new_skill_${items.length + 1}`,
        new_name: `new_skill_${items.length + 1}`,
      },
    ]);
  }, [items]);

  const handleRemoveRename = useCallback(
    (index: number) => {
      setItems(items.filter((_, i) => i !== index));
    },
    [items],
  );

  const handleNameChange = useCallback(
    (index: number, value: string) => {
      const next = [...items];
      next[index] = { ...next[index], new_name: value };
      setItems(next);
    },
    [items],
  );

  const conflictRenameModal = (
    <Modal
      open={items.length > 0}
      title={t("skillPool.multiConflictTitle", "Resolve Name Conflicts")}
      onCancel={handleCancel}
      footer={
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <Button onClick={handleAddRename} icon={<PlusOutlined />}>
            {t("common.add", "Add")}
          </Button>
          <div style={{ display: "flex", gap: 8 }}>
            <Button onClick={handleCancel}>{t("common.cancel")}</Button>
            <Button type="primary" onClick={handleOk}>
              {t("common.confirm")}
            </Button>
          </div>
        </div>
      }
    >
      <p style={{ marginBottom: 16, color: "#8c8c8c" }}>
        {t("skillPool.multiConflictDesc", "Please rename the conflicting skills")}
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {items.map((item, i) => (
          <div
            key={item.key}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <div style={{ minWidth: 120, fontWeight: 500 }}>
              {t("skillPool.renameEntry", { name: item.label, defaultValue: item.label })}
            </div>
            <Input
              value={item.new_name}
              onChange={(e) => handleNameChange(i, e.target.value)}
              style={{ flex: 1 }}
            />
            {items.length > 1 && (
              <Button
                danger
                size="small"
                icon={<DeleteOutlined />}
                onClick={() => handleRemoveRename(i)}
              />
            )}
          </div>
        ))}
      </div>
    </Modal>
  );

  return { showConflictRenameModal, conflictRenameModal };
}
