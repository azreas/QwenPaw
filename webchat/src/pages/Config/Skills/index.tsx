import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";
import {
  Button,
  Switch,
  Checkbox,
  Typography,
  message,
  Input,
  Upload,
  Tooltip,
} from "antd";
import {
  PlusOutlined,
  UploadOutlined,
  ReloadOutlined,
  DeleteOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  DownloadOutlined,
  SwapOutlined,
  ImportOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useTheme } from "../../../contexts/ThemeContext";
import { agentApi, type SkillSpec, type PoolSkillSpec } from "../../../api/modules/agent";
import { SkillCard, getSkillVisual } from "./components/SkillCard";
import { SkillDrawer, type SkillDrawerFormValues } from "./components/SkillDrawer";
import { SkillFilterDropdown } from "./components/SkillFilterDropdown";
import { PoolTransferModal } from "./components/PoolTransferModal";
import { ImportHubModal } from "./components/ImportHubModal";
import { useConflictRenameModal, type ConflictItem } from "./components/useConflictRenameModal";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import styles from "./Skills.module.css";

dayjs.extend(relativeTime);

const { Text } = Typography;

export default function SkillsConfig() {
  const { t } = useTranslation();
  const { isDark } = useTheme();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showConflictRenameModal, conflictRenameModal } = useConflictRenameModal();

  // 状态管理
  const [skills, setSkills] = useState<SkillSpec[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingSkill, setEditingSkill] = useState<SkillSpec | null>(null);
  const [viewMode, setViewMode] = useState<"card" | "list">("card");
  const [batchMode, setBatchMode] = useState(false);
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [poolModal, setPoolModal] = useState<"upload" | "download" | null>(null);
  const [poolSkills, setPoolSkills] = useState<PoolSkillSpec[]>([]);
  const [importModalOpen, setImportModalOpen] = useState(false);

  // 加载技能池列表（仅在打开模态框时）
  useEffect(() => {
    if (poolModal === "upload" || poolModal === "download") {
      agentApi.listSkillPoolSkills()
        .then(setPoolSkills)
        .catch(() => undefined);
    }
  }, [poolModal]);

  // 加载技能列表
  const loadSkills = useCallback(async () => {
    setLoading(true);
    try {
      const data = await agentApi.listSkills();
      setSkills(data);
    } catch (error) {
      console.error("Failed to load skills:", error);
      message.error(t("common.error"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadSkills();
  }, [loadSkills]);

  // 提取所有唯一标签
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    skills.forEach((skill) => {
      skill.tags?.forEach((tag) => tagSet.add(tag));
    });
    return Array.from(tagSet).sort();
  }, [skills]);

  // 过滤技能
  const filteredSkills = useMemo(() => {
    const filtered = skills.filter((skill) => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchName = skill.name.toLowerCase().includes(query);
        const matchDesc = skill.description.toLowerCase().includes(query);
        if (!matchName && !matchDesc) return false;
      }

      if (selectedTags.length > 0) {
        const hasTag = selectedTags.some((tag) => skill.tags?.includes(tag));
        if (!hasTag) return false;
      }

      return true;
    });

    return filtered.sort((a, b) => {
      if (a.enabled !== b.enabled) {
        return a.enabled ? -1 : 1;
      }
      return a.name.localeCompare(b.name);
    });
  }, [skills, searchQuery, selectedTags]);

  // 切换技能启用状态
  const handleToggleSkill = async (skill: SkillSpec) => {
    if (skill.installed === false && skill.installable) {
      await handleImportUploaded(skill);
      return;
    }
    try {
      await agentApi.toggleSkill(skill.name, !skill.enabled);
      message.success(t("common.success"));
      await loadSkills();
    } catch (error) {
      console.error("Failed to toggle skill:", error);
      message.error(t("common.error"));
    }
  };

  const handleImportUploaded = async (skill: SkillSpec) => {
    try {
      await agentApi.importUploadedSkill({
        skill_name: skill.name,
        overwrite: false,
      });
      message.success(t("skills.importUploadedSuccess"));
      await loadSkills();
    } catch (error) {
      console.error("Failed to import uploaded skill:", error);
      message.error(t("skills.importUploadedFailed"));
    }
  };

  // 创建技能
  const handleCreate = () => {
    setEditingSkill(null);
    setDrawerOpen(true);
  };

  // 编辑技能
  const handleEdit = async (skill: SkillSpec) => {
    try {
      setEditingSkill(skill);
      setDrawerOpen(true);
    } catch (error) {
      console.error("Failed to load skill content:", error);
      message.error(t("common.error"));
    }
  };

  // 保存技能
  const handleSave = async (values: SkillDrawerFormValues) => {
    try {
      if (editingSkill) {
        // 更新现有技能
        await agentApi.updateSkill(editingSkill.name, values.content, values.config);

        // 更新渠道和标签
        if (values.channels) {
          await agentApi.updateSkillChannels(editingSkill.name, values.channels);
        }
        if (values.tags) {
          await agentApi.updateSkillTags(editingSkill.name, values.tags);
        }

        message.success(t("skills.updatedSuccessfully"));
      } else {
        // 创建新技能
        await agentApi.createSkill({
          name: values.name,
          content: values.content,
          config: values.config,
          enable: values.enabled,
        });
        message.success(t("skills.createdSuccessfully"));
      }

      await loadSkills();
    } catch (error) {
      console.error("Failed to save skill:", error);
      throw error;
    }
  };

  // 删除技能
  const handleDelete = async (skillName: string) => {
    try {
      await agentApi.deleteSkill(skillName);
      message.success(t("skills.deletedSuccessfully"));
      await loadSkills();
    } catch (error) {
      console.error("Failed to delete skill:", error);
      message.error(t("common.error"));
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedSkills.size === 0) return;

    try {
      await agentApi.batchDeleteSkills(Array.from(selectedSkills));
      message.success(t("skills.batchDeletedSuccessfully"));
      setSelectedSkills(new Set());
      await loadSkills();
    } catch (error) {
      console.error("Failed to batch delete skills:", error);
      message.error(t("common.error"));
    }
  };

  // 切换选择
  const toggleSelection = (skillName: string) => {
    const newSelected = new Set(selectedSkills);
    if (newSelected.has(skillName)) {
      newSelected.delete(skillName);
    } else {
      newSelected.add(skillName);
    }
    setSelectedSkills(newSelected);
  };

  // 上传技能到技能池
  const handleUploadToPool = async (skillNames: string[]) => {
    if (skillNames.length === 0) return;

    try {
      for (const skillName of skillNames) {
        let newName: string | undefined;
        while (true) {
          try {
            await agentApi.uploadSkillToPool({
              skill_name: skillName,
              new_name: newName,
            });
            break;
          } catch (error: any) {
            const detail = error.response?.data?.detail || error.message;
            if (typeof detail === "object" && detail?.suggested_name) {
              const renameMap = await showConflictRenameModal([{
                key: skillName,
                label: skillName,
                suggested_name: detail.suggested_name,
              }]);
              if (!renameMap) return;
              newName = Object.values(renameMap)[0];
            } else {
              throw error;
            }
          }
        }
      }
      message.success(t("skills.uploadedToPool"));
      setPoolModal(null);
      await loadSkills();
    } catch (error) {
      console.error("Failed to upload to pool:", error);
      message.error(t("skills.uploadFailed"));
    }
  };

  // 从技能池下载技能
  const handleDownloadFromPool = async (poolSkillNames: string[]) => {
    if (poolSkillNames.length === 0) return;

    try {
      for (const skillName of poolSkillNames) {
        let targetName: string | undefined;
        while (true) {
          try {
            await agentApi.downloadSkillFromPool({
              skill_name: skillName,
              target_name: targetName,
            });
            break;
          } catch (error: any) {
            const detail = error.response?.data?.detail || error.message;
            if (typeof detail === "object" && detail?.suggested_name) {
              const renameMap = await showConflictRenameModal([{
                key: skillName,
                label: skillName,
                suggested_name: detail.suggested_name,
              }]);
              if (!renameMap) return;
              targetName = Object.values(renameMap)[0];
            } else {
              throw error;
            }
          }
        }
      }
      message.success(t("skills.downloadedToWorkspace"));
      setPoolModal(null);
      await loadSkills();
    } catch (error) {
      console.error("Failed to download from pool:", error);
      message.error(t("common.error"));
    }
  };

  // 上传ZIP文件
  const handleUploadZip = async (file: File) => {
    setUploading(true);
    try {
      let renameMap: Record<string, string> | undefined;
      while (true) {
        const result = await agentApi.uploadSkillZip(
          file,
          true,
          false,
          "",
          renameMap ? JSON.stringify(renameMap) : undefined
        );

        if (!result.conflicts || result.conflicts.length === 0) break;

        const conflicts: ConflictItem[] = result.conflicts.map((name: string) => ({
          key: name,
          label: name,
          suggested_name: `${name}_${Date.now()}`,
        }));

        const newRenames = await showConflictRenameModal(conflicts);
        if (!newRenames) break;
        renameMap = { ...renameMap, ...newRenames };
      }

      message.success(t("skills.uploadZipSuccess"));
      await loadSkills();
    } catch (error) {
      console.error("Failed to upload zip:", error);
      message.error(t("skills.uploadFailed"));
    } finally {
      setUploading(false);
    }
    return false;
  };

  // 从Skills Hub导入
  const handleImportFromHub = async (url: string, targetName?: string) => {
    setImporting(true);
    try {
      await agentApi.importSkillFromHub({
        bundle_url: url,
        target_name: targetName,
      });
      message.success(t("skills.importHubSuccess"));
      setImportModalOpen(false);
      await loadSkills();
    } catch (error: any) {
      const detail = error.response?.data?.detail || error.message;
      if (typeof detail === "object" && detail?.suggested_name) {
        const renameMap = await showConflictRenameModal([{
          key: targetName || "imported",
          label: targetName || "Imported Skill",
          suggested_name: detail.suggested_name,
        }]);
        if (renameMap) {
          const newName = Object.values(renameMap)[0];
          await handleImportFromHub(url, newName);
        }
      } else {
        console.error("Failed to import from hub:", error);
        message.error(t("skills.importHubFailed"));
      }
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className={styles.skillsPage}>
      {/* Page Header */}
      <div className={styles.pageHeader}>
        <div className={styles.breadcrumbHeader}>
          <span className={styles.breadcrumbParent}>{t("config.workspace")}</span>
          <span className={styles.breadcrumbSeparator}>/</span>
          <span className={styles.breadcrumbCurrent}>{t("config.skills")}</span>
        </div>
        <div className={styles.headerRight}>
          {/* 从技能池载入 */}
          <Tooltip title={t("skills.downloadFromPoolHint")}>
            <Button
              icon={<DownloadOutlined />}
              onClick={() => setPoolModal("download")}
            >
              {t("skills.downloadFromPool")}
            </Button>
          </Tooltip>

          {/* 同步到技能池 */}
          <Tooltip title={t("skills.uploadToPoolHint")}>
            <Button
              icon={<SwapOutlined />}
              onClick={() => setPoolModal("upload")}
            >
              {t("skills.uploadToPool")}
            </Button>
          </Tooltip>

          {/* 通过zip上传 */}
          <Upload
            beforeUpload={handleUploadZip}
            showUploadList={false}
            accept=".zip"
          >
            <Button icon={<UploadOutlined />} loading={uploading}>
              {t("skills.uploadZip")}
            </Button>
          </Upload>

          {/* 从Skills Hub导入 */}
          <Tooltip title={t("skills.importHubHint")}>
            <Button
              icon={<ImportOutlined />}
              onClick={() => setImportModalOpen(true)}
            >
              {t("skills.importHub")}
            </Button>
          </Tooltip>

          {/* 刷新 */}
          <Tooltip title={t("common.refresh")}>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadSkills}
              loading={loading}
            />
          </Tooltip>

          {/* 批量模式 */}
          <Tooltip title={t("skills.batchMode")}>
            <Button
              icon={<DeleteOutlined />}
              type={batchMode ? "primary" : "default"}
              onClick={() => {
                setBatchMode(!batchMode);
                setSelectedSkills(new Set());
              }}
            />
          </Tooltip>

          {/* 创建 */}
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            {t("common.create")}
          </Button>
        </div>
      </div>

      {/* Toolbar: Search + View Toggle */}
      {!loading && skills.length > 0 && (
        <div className={styles.toolbar}>
          <div className={styles.searchContainer}>
            <Input.Search
              placeholder={t("skills.search")}
              style={{ flex: 1, minWidth: 200 }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              allowClear
              prefix={<SearchOutlined />}
            />
            <SkillFilterDropdown
              tags={allTags}
              selectedTags={selectedTags}
              onChange={setSelectedTags}
            />
          </div>
          <div className={styles.toolbarRight}>
            <div className={styles.viewToggle}>
              <Tooltip title={viewMode === "card" ? t("skills.listView") : t("skills.cardView")}>
                <button
                  className={`${styles.viewToggleBtn} ${viewMode === "list" ? styles.viewToggleBtnActive : ""}`}
                  onClick={() => setViewMode(viewMode === "card" ? "list" : "card")}
                >
                  <UnorderedListOutlined />
                </button>
              </Tooltip>
              <Tooltip title={viewMode === "card" ? t("skills.listView") : t("skills.cardView")}>
                <button
                  className={`${styles.viewToggleBtn} ${viewMode === "card" ? styles.viewToggleBtnActive : ""}`}
                  onClick={() => setViewMode(viewMode === "card" ? "list" : "card")}
                >
                  <AppstoreOutlined />
                </button>
              </Tooltip>
            </div>
          </div>
        </div>
      )}

      {/* Batch Actions Bar */}
      {batchMode && selectedSkills.size > 0 && (
        <div className={styles.batchActions}>
          <Text strong className={styles.batchCount}>
            {t("skills.selectedCount")}: {selectedSkills.size}
          </Text>
          <Button danger onClick={handleBatchDelete}>
            {t("skills.batchDelete")}
          </Button>
          <Button onClick={() => setSelectedSkills(new Set())}>
            {t("skills.clearSelection")}
          </Button>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className={styles.loadingContainer}>
          <span className={styles.loadingText}>{t("common.loading")}</span>
        </div>
      ) : skills.length === 0 ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyStateBadge}>Skills</div>
          <h2 className={styles.emptyStateTitle}>{t("skills.noSkills")}</h2>
          <p className={styles.emptyStateText}>{t("skills.emptyStateText")}</p>
          <div className={styles.emptyStateActions}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              {t("skills.emptyStateCreate")}
            </Button>
          </div>
        </div>
      ) : filteredSkills.length === 0 ? (
        <div className={styles.noSearchResults}>
          <span className={styles.noSearchResultsIcon}>🔍</span>
          <span className={styles.noSearchResultsText}>{t("skills.noSearchResults")}</span>
        </div>
      ) : viewMode === "card" ? (
        <div className={styles.skillsGrid}>
          {filteredSkills.map((skill) => (
            <SkillCard
              key={skill.name}
              skill={skill}
              selected={selectedSkills.has(skill.name)}
              batchMode={batchMode}
              onSelect={() => toggleSelection(skill.name)}
              onClick={() =>
                skill.installed === false && skill.installable
                  ? undefined
                  : handleEdit(skill)
              }
              onToggleEnabled={(_e) => handleToggleSkill(skill)}
              onImport={(_e) => handleImportUploaded(skill)}
              onDelete={(_e) => handleDelete(skill.name)}
            />
          ))}
        </div>
      ) : (
        /* List View */
        <div className={styles.skillsList}>
          {filteredSkills.map((skill) => (
            <div
              key={skill.name}
              className={styles.skillListItem}
              onClick={() => {
                if (!(skill.installed === false && skill.installable)) {
                  handleEdit(skill);
                }
              }}
            >
              <div className={styles.listItemLeft}>
                <span style={{ fontSize: 28 }}>
                  {getSkillVisual(skill.name, skill.emoji)}
                </span>
                <div className={styles.listItemInfo}>
                  <div className={styles.listItemHeader}>
                    <Text strong style={{ fontSize: 16 }}>{skill.name}</Text>
                    {(skill.source === "builtin" || skill.source?.startsWith("builtin:")) && (
                      <span className={styles.typeBadge}>{t("skills.builtin")}</span>
                    )}
                    {skill.installed === false && skill.installable && (
                      <span className={styles.typeBadge}>{t("skills.uploadedMedia")}</span>
                    )}
                    {(!skill.source || skill.source === "customized") && (
                      <span className={styles.typeBadge}>{t("skills.custom")}</span>
                    )}
                  </div>
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    {skill.description || "-"}
                  </Text>
                  {skill.last_updated && (
                    <span className={styles.listItemTime}>
                      {dayjs(skill.last_updated).fromNow()}
                    </span>
                  )}
                </div>
              </div>
              <div className={styles.listItemRight}>
                {batchMode && !(skill.installed === false && skill.installable) && (
                  <Checkbox checked={selectedSkills.has(skill.name)} onClick={(e) => { e.stopPropagation(); toggleSelection(skill.name); }} />
                )}
                {skill.installed === false && skill.installable ? (
                  <Button
                    type="primary"
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleImportUploaded(skill);
                    }}
                  >
                    {t("skills.importUploadedSkill")}
                  </Button>
                ) : (
                  <>
                    <Switch
                      checked={skill.enabled}
                      onChange={() => handleToggleSkill(skill)}
                      size="small"
                    />
                    <Button
                      type="text"
                      size="small"
                      danger
                      onClick={(e) => { e.stopPropagation(); handleDelete(skill.name); }}
                    >
                      {t("common.delete")}
                    </Button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 技能编辑抽屉 */}
      <SkillDrawer
        open={drawerOpen}
        skill={editingSkill}
        onClose={() => {
          setDrawerOpen(false);
          setEditingSkill(null);
        }}
        onSave={handleSave}
        isDark={isDark}
      />

      {/* 技能池传输模态框 */}
      <PoolTransferModal
        mode={poolModal}
        skills={skills}
        poolSkills={poolSkills}
        onCancel={() => setPoolModal(null)}
        onUpload={handleUploadToPool}
        onDownload={handleDownloadFromPool}
      />

      {/* Skills Hub导入模态框 */}
      <ImportHubModal
        open={importModalOpen}
        importing={importing}
        onCancel={() => setImportModalOpen(false)}
        onConfirm={handleImportFromHub}
      />

      {/* 冲突重命名模态框 */}
      {conflictRenameModal}

      {/* 隐藏的文件上传输入 */}
      <input
        type="file"
        accept=".zip"
        ref={fileInputRef}
        style={{ display: "none" }}
      />
    </div>
  );
}
