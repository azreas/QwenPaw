import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Modal, Button, Checkbox } from "antd";
import type { PoolSkillSpec, SkillSpec } from "../../../../api/modules/agent";
import styles from "./PoolTransferModal.module.less";

interface PoolTransferModalProps {
  mode: "upload" | "download" | null;
  skills: SkillSpec[];
  poolSkills: PoolSkillSpec[];
  onCancel: () => void;
  onUpload: (skillNames: string[]) => Promise<void>;
  onDownload: (poolSkillNames: string[]) => Promise<void>;
}

export function PoolTransferModal({
  mode,
  skills,
  poolSkills,
  onCancel,
  onUpload,
  onDownload,
}: PoolTransferModalProps) {
  const { t } = useTranslation();
  const [workspaceSkillNames, setWorkspaceSkillNames] = useState<string[]>([]);
  const [poolSkillNames, setPoolSkillNames] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const isUpload = mode === "upload";
  const selectedNames = isUpload ? workspaceSkillNames : poolSkillNames;
  const items = isUpload ? skills : poolSkills;

  const setSelectedNames = isUpload ? setWorkspaceSkillNames : setPoolSkillNames;

  const handleConfirm = useCallback(async () => {
    if (selectedNames.length === 0) return;

    setLoading(true);
    try {
      if (isUpload) {
        await onUpload(selectedNames);
      } else {
        await onDownload(selectedNames);
      }
    } finally {
      setLoading(false);
    }
  }, [isUpload, onUpload, onDownload, selectedNames]);

  const handleSelectAll = useCallback(() => {
    if (selectedNames.length === items.length) {
      setSelectedNames([]);
    } else {
      setSelectedNames(items.map((item) => item.name));
    }
  }, [items, selectedNames, setSelectedNames]);

  if (mode === null) return null;

  return (
    <Modal
      open={mode !== null}
      title={isUpload ? t("skills.uploadToPool") : t("skills.downloadFromPool")}
      width={600}
      onCancel={onCancel}
      footer={
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <Button onClick={onCancel}>{t("common.cancel")}</Button>
          <Button
            type="primary"
            loading={loading}
            disabled={selectedNames.length === 0}
            onClick={handleConfirm}
          >
            {t("common.confirm")} ({selectedNames.length})
          </Button>
        </div>
      }
    >
      <div style={{ marginBottom: 16 }}>
        <Checkbox
          checked={selectedNames.length === items.length && items.length > 0}
          indeterminate={selectedNames.length > 0 && selectedNames.length < items.length}
          onChange={handleSelectAll}
        >
          {t("skills.selectAll")}
        </Checkbox>
      </div>

      <div className={styles.pickerGrid}>
        {items.map((skill) => {
          const selected = selectedNames.includes(skill.name);
          return (
            <div
              key={skill.name}
              className={`${styles.pickerCard} ${selected ? styles.pickerCardSelected : ""
                }`}
              onClick={() =>
                setSelectedNames(
                  selected
                    ? selectedNames.filter((n) => n !== skill.name)
                    : [...selectedNames, skill.name]
                )
              }
            >
              <div className={styles.pickerCardCheckbox}>
                <Checkbox checked={selected} />
              </div>
              <div className={styles.pickerCardName}>{skill.name}</div>
              <div className={styles.pickerCardDesc}>
                {skill.description || "-"}
              </div>
            </div>
          );
        })}
      </div>

      {items.length === 0 && (
        <div style={{ textAlign: "center", padding: "40px 0", color: "#999" }}>
          {isUpload ? t("skills.noSkillsToUpload") : t("skills.noSkillsInPool")}
        </div>
      )}
    </Modal>
  );
}
