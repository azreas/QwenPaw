import { useState } from "react";
import { Card, Button, Checkbox, Tooltip } from "antd";
import {
  CalendarFilled,
  FileTextFilled,
  FileZipFilled,
  FilePdfFilled,
  FileWordFilled,
  FileExcelFilled,
  FilePptFilled,
  FileImageFilled,
  CodeFilled,
  EyeOutlined,
  EyeInvisibleOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import type { SkillSpec } from "../../../../api/modules/agent";
import { useTranslation } from "react-i18next";
import styles from "../Skills.module.css";

dayjs.extend(relativeTime);

interface SkillCardProps {
  skill: SkillSpec;
  selected?: boolean;
  batchMode?: boolean;
  onSelect?: () => void;
  onClick: () => void;
  onToggleEnabled: (e: React.MouseEvent) => void;
  onImport?: (e: React.MouseEvent) => void;
  onDelete: (e: React.MouseEvent) => void;
}

const normalizeSkillIconKey = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .split(/\s+/)[0]
    ?.replace(/[^a-z0-9_-]/g, "") || "";

const getFileIcon = (filePath: string) => {
  const skillKey = normalizeSkillIconKey(filePath);
  const textSkillIcons = new Set([
    "news",
    "file_reader",
    "browser_visible",
    "guidance",
    "himalaya",
    "dingtalk_channel",
  ]);

  if (textSkillIcons.has(skillKey)) {
    return <FileTextFilled style={{ color: "#1890ff" }} />;
  }

  switch (skillKey) {
    case "docx":
      return <FileWordFilled style={{ color: "#2B8DFF" }} />;
    case "xlsx":
      return <FileExcelFilled style={{ color: "#44C161" }} />;
    case "pptx":
      return <FilePptFilled style={{ color: "#FF5B3B" }} />;
    case "pdf":
      return <FilePdfFilled style={{ color: "#F04B57" }} />;
    case "cron":
      return <CalendarFilled style={{ color: "#13c2c2" }} />;
    default:
      break;
  }

  const extension = filePath.split(".").pop()?.toLowerCase() || "";

  switch (extension) {
    case "txt":
    case "md":
    case "markdown":
      return <FileTextFilled style={{ color: "#1890ff" }} />;
    case "zip":
    case "rar":
    case "7z":
    case "tar":
    case "gz":
      return <FileZipFilled style={{ color: "#fa8c16" }} />;
    case "pdf":
      return <FilePdfFilled style={{ color: "#F04B57" }} />;
    case "doc":
    case "docx":
      return <FileWordFilled style={{ color: "#2B8DFF" }} />;
    case "xls":
    case "xlsx":
      return <FileExcelFilled style={{ color: "#44C161" }} />;
    case "ppt":
    case "pptx":
      return <FilePptFilled style={{ color: "#FF5B3B" }} />;
    case "jpg":
    case "jpeg":
    case "png":
    case "gif":
    case "svg":
    case "webp":
      return <FileImageFilled style={{ color: "#eb2f96" }} />;
    case "py":
    case "js":
    case "ts":
    case "jsx":
    case "tsx":
    case "java":
    case "cpp":
    case "c":
    case "go":
    case "rs":
    case "rb":
    case "php":
      return <CodeFilled style={{ color: "#52c41a" }} />;
    default:
      return <FileTextFilled style={{ color: "#1890ff" }} />;
  }
};

const getSkillVisual = (name: string, emoji?: string) => {
  if (emoji) {
    return <span className={styles.skillEmoji}>{emoji}</span>;
  }
  return getFileIcon(name);
};

export { getSkillVisual };

export function SkillCard({
  skill,
  selected,
  batchMode,
  onSelect,
  onClick,
  onToggleEnabled,
  onImport,
  onDelete,
}: SkillCardProps) {
  const { t } = useTranslation();
  const [isHover, setIsHover] = useState(false);

  const handleSelectClick = (_e: React.MouseEvent) => {
    _e.stopPropagation();
    onSelect?.();
  };

  const handleToggleClick = (_e: React.MouseEvent) => {
    _e.stopPropagation();
    onToggleEnabled(_e);
  };

  const handleDeleteClick = (_e: React.MouseEvent) => {
    _e.stopPropagation();
    onDelete(_e);
  };

  const handleImportClick = (_e: React.MouseEvent) => {
    _e.stopPropagation();
    onImport?.(_e);
  };

  const handleCardClick = (_e: React.MouseEvent) => {
    if (batchMode && onSelect && !isUploadedCandidate) {
      onSelect();
    } else {
      onClick();
    }
  };

  const isBuiltin =
    skill.source === "builtin" ||
    skill.source?.startsWith("builtin:") ||
    skill.source === "system";
  const isUploadedCandidate = skill.installed === false && skill.installable;

  return (
    <Card
      hoverable
      onClick={handleCardClick}
      onMouseEnter={() => setIsHover(true)}
      onMouseLeave={() => setIsHover(false)}
      className={`${styles.skillCard} ${selected ? styles.skillCardSelected : ""}`}
      style={{ cursor: "pointer" }}
    >
      {/* Top row: Icon + Status badge + Checkbox */}
      <div className={styles.cardTopRow}>
        <span className={styles.fileIcon}>
          {getSkillVisual(skill.name, skill.emoji)}
        </span>
        <div className={styles.cardTopRight}>
          <span
            className={`${styles.statusBadge} ${
              skill.enabled && !isUploadedCandidate
                ? styles.statusEnabled
                : styles.statusDisabled
            }`}
          >
            <span className={styles.statusDot} />
            {isUploadedCandidate
              ? t("skills.pendingInstall")
              : skill.enabled
                ? t("common.enabled")
                : t("common.disabled")}
          </span>
          {batchMode && !isUploadedCandidate && (
            <Checkbox checked={selected} onClick={handleSelectClick} />
          )}
        </div>
      </div>

      {/* Title + Built-in/Custom tag */}
      <div className={styles.titleRow}>
        <Tooltip title={skill.name}>
          <h3 className={styles.skillTitle}>
            {skill.name}{" "}
            {isUploadedCandidate ? (
              <span className={styles.customTag}>{t("skills.uploadedMedia")}</span>
            ) : isBuiltin ? (
              <span className={styles.builtinTag}>{t("skills.builtin")}</span>
            ) : (
              <span className={styles.customTag}>{t("skills.custom")}</span>
            )}
          </h3>
        </Tooltip>
      </div>

      {/* Channels row */}
      <div className={styles.metaInfoRow}>
        <span className={styles.metaInfoLabel}>{t("skills.channels")}</span>
        <span className={styles.metaInfoValue}>
          {(skill.channels || ["all"])
            .map((ch) => (ch === "all" ? t("skills.allChannels") : ch))
            .join(", ")}
        </span>
      </div>

      {/* Updated row */}
      {skill.last_updated && (
        <div className={styles.metaInfoRow}>
          <span className={styles.metaInfoLabel}>{t("skills.lastUpdated")}</span>
          <span className={styles.metaInfoValue}>
            {dayjs(skill.last_updated).fromNow()}
          </span>
        </div>
      )}

      {/* Tags row */}
      <div className={styles.metaInfoRow}>
        <span className={styles.metaInfoLabel}>{t("skills.tags")}</span>
        {!!skill.tags?.length ? (
          <div className={styles.tagChips}>
            {skill.tags.map((tag: string) => (
              <span key={tag} className={styles.tagChip}>
                {tag}
              </span>
            ))}
          </div>
        ) : (
          <span style={{ color: "rgba(20,20,19,0.35)" }}>-</span>
        )}
      </div>

      {/* Description */}
      <div className={styles.descriptionSection}>
        <span className={styles.descriptionSectionLabel}>
          {t("skills.skillDescription")}
        </span>
        <p className={styles.descriptionText}>{skill.description || "-"}</p>
      </div>

      {/* Footer - only show on hover or batch mode */}
      {(isHover || batchMode) && (
        <div className={styles.cardFooter}>
          {isUploadedCandidate ? (
            <Button
              type="primary"
              className={styles.actionButton}
              disabled={batchMode}
              onClick={handleImportClick}
            >
              {t("skills.importUploadedSkill")}
            </Button>
          ) : (
            <>
              <Button
                type="default"
                className={styles.actionButton}
                disabled={batchMode}
                onClick={handleToggleClick}
                icon={skill.enabled ? <EyeInvisibleOutlined /> : <EyeOutlined />}
              >
                {skill.enabled ? t("common.disable") : t("common.enable")}
              </Button>
              <Button
                danger
                className={styles.deleteButton}
                disabled={batchMode}
                onClick={handleDeleteClick}
              >
                {t("common.delete")}
              </Button>
            </>
          )}
        </div>
      )}
    </Card>
  );
}
