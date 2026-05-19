import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Button,
  Switch,
  Spin,
  message,
  Input,
  Tooltip,
  Card,
  Popconfirm,
} from "antd";
import {
  UploadOutlined,
  DownloadOutlined,
  SaveOutlined,
  ReloadOutlined,
  UndoOutlined,
  CopyOutlined,
  CaretDownOutlined,
  CaretRightOutlined,
  HolderOutlined,
  DeleteOutlined,
  FileOutlined,
  FolderOutlined,
} from "@ant-design/icons";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { XMarkdown } from "@ant-design/x-markdown";
import { getApiUrl, getAuthHeaders } from "../../../api/config";
import { agentApi } from "../../../api/modules/agent";
import { workspaceApi, WorkspaceEntry } from "../../../api/modules/workspace";
import { useTheme } from "../../../contexts/ThemeContext";
import styles from "./index.module.less";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MarkdownFile {
  filename: string;
  path: string;
  size: number;
  created_time?: string;
  modified_time?: string;
  updated_at?: string;
}

interface DailyMemoryFile {
  date: string;
  path: string;
  size: number;
  created_time: string;
  modified_time: string;
  updated_at: string | number;
}

interface FileItemProps {
  file: MarkdownFile;
  selectedFile: MarkdownFile | null;
  expandedMemory: boolean;
  dailyMemories: DailyMemoryFile[];
  enabled: boolean;
  onFileClick: (file: MarkdownFile) => void;
  onDailyMemoryClick: (daily: DailyMemoryFile) => void;
  onToggleEnabled: (filename: string) => void;
}

// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

/** 格式化文件大小 */
const formatFileSize = (bytes: number): string => {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
};

/** 格式化时间（相对时间） */
const formatTimeAgo = (timeStr?: string | number, t?: (key: string, options?: Record<string, any>) => string): string => {
  if (!timeStr) return "-";
  const date = typeof timeStr === 'number' ? new Date(timeStr) : new Date(timeStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (!t) {
    // Fallback without i18n
    if (diffDay > 30) {
      const months = Math.floor(diffDay / 30);
      return `${months}个月前`;
    } else if (diffDay > 0) {
      return `${diffDay}天前`;
    } else if (diffHour > 0) {
      return `${diffHour}小时前`;
    } else if (diffMin > 0) {
      return `${diffMin}分钟前`;
    } else {
      return "刚刚";
    }
  }

  // Use i18n
  if (diffDay > 30) {
    const months = Math.floor(diffDay / 30);
    return t("common.timeAgo.monthsAgo", { count: months });
  } else if (diffDay > 0) {
    return t("common.timeAgo.daysAgo", { count: diffDay });
  } else if (diffHour > 0) {
    return t("common.timeAgo.hoursAgo", { count: diffHour });
  } else if (diffMin > 0) {
    return t("common.timeAgo.minutesAgo", { count: diffMin });
  } else {
    return t("common.timeAgo.justNow");
  }
};

/** 获取文件的父目录 */
const getParentDir = (filePath: string): string => {
  const match = filePath.match(/^(.*)[/\\]/);
  return match ? match[1] : filePath;
};

/** 从内容中移除 frontmatter */
const stripFrontmatter = (content: string): string => {
  const match = content.match(/^---[\s\S]*?---\n?/);
  return match ? content.slice(match[0].length) : content;
};

// ---------------------------------------------------------------------------
// FileItem Component
// ---------------------------------------------------------------------------

const SortableFileItem: React.FC<
  FileItemProps & { disabled: boolean }
> = ({
  file,
  selectedFile,
  expandedMemory,
  dailyMemories,
  enabled,
  disabled,
  onFileClick,
  onDailyMemoryClick,
  onToggleEnabled,
}) => {
  const { t } = useTranslation();
  const isSelected = selectedFile?.filename === file.filename;
  const isMemoryFile = file.filename === "MEMORY.md";

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: file.filename,
    disabled: disabled || !enabled,
  });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    position: "relative",
    zIndex: isDragging ? 1 : undefined,
  };

  const handleToggleClick = (
    _checked: boolean,
    event:
      | React.MouseEvent<HTMLButtonElement>
      | React.KeyboardEvent<HTMLButtonElement>,
  ) => {
    event.stopPropagation();
    onToggleEnabled(file.filename);
  };

  return (
    <div ref={setNodeRef} style={style}>
      <div
        onClick={() => onFileClick(file)}
        className={`${styles.fileItem} ${isSelected ? styles.selected : ""} ${
          isDragging ? styles.dragging : ""
        }`}
      >
        <div className={styles.fileItemHeader}>
          {enabled && (
            <div
              className={styles.dragHandle}
              {...attributes}
              {...listeners}
              onClick={(e) => e.stopPropagation()}
            >
              <HolderOutlined />
            </div>
          )}
          <div className={styles.fileInfo}>
            <div className={styles.fileItemName}>
              {enabled && <span className={styles.enabledBadge}>●</span>}
              {file.filename}
            </div>
            <div className={styles.fileItemMeta}>
              {formatFileSize(file.size)} ·{" "}
              {formatTimeAgo(file.modified_time || file.created_time, t)}
            </div>
          </div>
          <div className={styles.fileItemActions}>
            <Tooltip title={t("workspace.systemPromptToggleTooltip")}>
              <Switch
                size="small"
                checked={enabled}
                onClick={handleToggleClick}
              />
            </Tooltip>
            {isMemoryFile && (
              <span className={styles.expandIcon}>
                {expandedMemory ? <CaretDownOutlined /> : <CaretRightOutlined />}
              </span>
            )}
          </div>
        </div>
      </div>

      {isMemoryFile && expandedMemory && (
        <div className={styles.dailyMemoryList}>
          {dailyMemories.map((daily) => {
            const isDailySelected =
              selectedFile?.filename === `${daily.date}.md`;
            return (
              <div
                key={daily.date}
                onClick={() => onDailyMemoryClick(daily)}
                className={`${styles.dailyMemoryItem} ${
                  isDailySelected ? styles.selected : ""
                }`}
              >
                <div className={styles.dailyMemoryName}>{daily.date}.md</div>
                <div className={styles.dailyMemoryMeta}>
                  {formatFileSize(daily.size)} ·{" "}
                  {formatTimeAgo(daily.updated_at, t)}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function FilesConfig() {
  const { t } = useTranslation();
  useTheme();
  const [files, setFiles] = useState<MarkdownFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<MarkdownFile | null>(null);
  const [dailyMemories, setDailyMemories] = useState<DailyMemoryFile[]>([]);
  const [expandedMemory, setExpandedMemory] = useState(false);
  const [fileContent, setFileContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [loadingFile, setLoadingFile] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [workspacePath, setWorkspacePath] = useState<string | null>(null);
  const [enabledFiles, setEnabledFiles] = useState<string[]>([]);
  const [showMarkdown, setShowMarkdown] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── 文件浏览器状态 ──
  const [dirEntries, setDirEntries] = useState<WorkspaceEntry[]>([]);
  const [loadingDir, setLoadingDir] = useState(false);
  const [currentPath, setCurrentPath] = useState("");

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
  );

  const hasChanges = fileContent !== originalContent;
  const isMarkdownFile = selectedFile?.filename.endsWith(".md") || false;
  const markdownContent = useMemo(
    () => stripFrontmatter(fileContent || ""),
    [fileContent],
  );

  // 加载文件列表
  const fetchFiles = useCallback(
    async (latestEnabledFiles?: string[]) => {
      try {
        const enabled = Array.isArray(latestEnabledFiles)
          ? latestEnabledFiles
          : await workspaceApi.getSystemPromptFiles();

        // 使用专门的API获取文件列表，与console保持一致
        const fileList = await agentApi.listAgentFiles();
        const transformedFiles: MarkdownFile[] = (fileList || []).map(
          (f: any) => ({
            filename: f.filename,
            path: f.path || f.filename,
            size: f.size || 0,
            created_time: f.created_time,
            modified_time: f.modified_time,
          }),
        );

        // 排序：启用文件按 enabledFiles 顺序置顶，未启用文件按字母排序
        const sortedFiles = [...transformedFiles].sort((a, b) => {
          const aIndex = enabled.indexOf(a.filename);
          const bIndex = enabled.indexOf(b.filename);
          const aEnabled = aIndex !== -1;
          const bEnabled = bIndex !== -1;

          if (aEnabled && bEnabled) return aIndex - bIndex;
          if (aEnabled) return -1;
          if (bEnabled) return 1;
          return a.filename.localeCompare(b.filename);
        });

        setFiles(sortedFiles);
        setEnabledFiles(enabled);

        // 设置工作区路径
        if (transformedFiles.length > 0) {
          setWorkspacePath(getParentDir(transformedFiles[0].path));
        } else {
          setWorkspacePath("");
        }
      } catch (error) {
        console.error("Failed to load files:", error);
        message.error(t("common.error"));
      }
    },
    [t],
  );

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  // ── 目录浏览逻辑 ──
  const fetchDirectory = useCallback(async (dirPath?: string) => {
    setLoadingDir(true);
    try {
      const result = await workspaceApi.listFiles(dirPath || "");
      setDirEntries(result.entries);
      setCurrentPath(result.path);
    } catch (error) {
      console.error("Failed to list directory:", error);
      message.error(t("common.error"));
    } finally {
      setLoadingDir(false);
    }
  }, [t]);

  // 初始加载时获取根目录
  useEffect(() => {
    fetchDirectory("");
  }, [fetchDirectory]);
  // 当 enabledFiles 变化时重新排序
  useEffect(() => {
    if (files.length > 0 && enabledFiles.length >= 0) {
      const sortedFiles = [...files].sort((a, b) => {
        const aIndex = enabledFiles.indexOf(a.filename);
        const bIndex = enabledFiles.indexOf(b.filename);
        const aEnabled = aIndex !== -1;
        const bEnabled = bIndex !== -1;

        if (aEnabled && bEnabled) return aIndex - bIndex;
        if (aEnabled) return -1;
        if (bEnabled) return 1;
        return a.filename.localeCompare(b.filename);
      });

      const orderChanged = sortedFiles.some(
        (file, index) => file.filename !== files[index]?.filename,
      );
      if (orderChanged) {
        setFiles(sortedFiles);
      }
    }
  }, [enabledFiles, files]);

  // 点击文件
  const handleFileClick = async (file: MarkdownFile) => {
    if (file.filename === "MEMORY.md") {
      if (expandedMemory && selectedFile?.filename === "MEMORY.md") {
        setExpandedMemory(false);
        return;
      } else {
        setExpandedMemory(true);
        fetchDailyMemories();
      }
    }

    setSelectedFile(file);
    setLoadingFile(true);
    try {
      const content = await agentApi.getFileContent(file.filename);
      setFileContent(content);
      setOriginalContent(content);
    } catch (error) {
      console.error("Failed to load file:", error);
      message.error(t("common.error"));
    } finally {
      setLoadingFile(false);
    }
  };

  // 点击每日记忆
  const handleDailyMemoryClick = async (daily: DailyMemoryFile) => {
    setSelectedFile({
      filename: `${daily.date}.md`,
      path: daily.path,
      size: daily.size,
      created_time: daily.created_time,
      modified_time: daily.modified_time,
      updated_at: typeof daily.updated_at === 'number' 
        ? new Date(daily.updated_at).toISOString() 
        : daily.updated_at,
    });
    setLoadingFile(true);
    try {
      const response = await workspaceApi.loadDailyMemory(daily.date);
      setFileContent(response.content);
      setOriginalContent(response.content);
    } catch (error) {
      console.error("Failed to load daily memory:", error);
      message.error(t("common.error"));
    } finally {
      setLoadingFile(false);
    }
  };

  // 加载每日记忆列表
  const fetchDailyMemories = async () => {
    try {
      const memoryList = await workspaceApi.listDailyMemory();
      setDailyMemories(memoryList);
    } catch (error) {
      console.error("Failed to fetch daily memories:", error);
    }
  };

  // ── 文件浏览器操作 ──
  const handleDeleteFile = async (entry: WorkspaceEntry) => {
    const filePath = currentPath ? `${currentPath}/${entry.name}` : entry.name;
    try {
      await workspaceApi.deleteWorkspaceFile(filePath);
      message.success(t("workspace.deleteSuccess"));
      fetchDirectory(currentPath);
    } catch (error) {
      message.error(t("workspace.deleteFailed"));
    }
  };

  const handleEnterDir = (entry: WorkspaceEntry) => {
    const newPath = currentPath ? `${currentPath}/${entry.name}` : entry.name;
    fetchDirectory(newPath);
  };

  const handleFileUploadToPath = async (file: File) => {
    try {
      await workspaceApi.uploadWorkspaceFile(file, currentPath || undefined);
      message.success(t("workspace.uploadSuccess"));
      fetchDirectory(currentPath);
    } catch (error) {
      message.error(t("workspace.uploadFailed"));
    }
  };

  // 保存文件
  const handleSave = async () => {
    if (!selectedFile) return;
    setSaving(true);
    try {
      if (selectedFile.filename.match(/^\d{4}-\d{2}-\d{2}\.md$/)) {
        const date = selectedFile.filename.replace(".md", "");
        await workspaceApi.saveDailyMemory(date, fileContent);
        fetchDailyMemories();
      } else {
        await agentApi.updateFileContent(selectedFile.filename, fileContent);
        fetchFiles();
      }
      setOriginalContent(fileContent);
      message.success(t("common.success"));
    } catch (error) {
      console.error("Failed to save file:", error);
      message.error(t("common.error"));
    } finally {
      setSaving(false);
    }
  };

  // 重置内容
  const handleReset = () => {
    setFileContent(originalContent);
  };

  // 切换文件启用状态
  const handleToggleFileEnabled = async (filename: string) => {
    const isEnabling = !enabledFiles.includes(filename);

    // MEMORY.md 启用时显示警告
    if (isEnabling && filename === "MEMORY.md") {
      message.warning({
        content: t("workspace.memoryFileWarning"),
        duration: 5,
      });
    }

    const newEnabledFiles = enabledFiles.includes(filename)
      ? enabledFiles.filter((f) => f !== filename)
      : [...enabledFiles, filename];

    try {
      await workspaceApi.setSystemPromptFiles(newEnabledFiles);
      setEnabledFiles(newEnabledFiles);
      message.success(t("workspace.configUpdated"));
    } catch (error) {
      console.error("Failed to update enabled files:", error);
      message.error(t("workspace.configUpdateFailed"));
    }
  };

  // 拖拽排序
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = enabledFiles.indexOf(active.id as string);
    const newIndex = enabledFiles.indexOf(over.id as string);
    if (oldIndex === -1 || newIndex === -1) return;

    const newOrder = arrayMove(enabledFiles, oldIndex, newIndex);
    handleReorderFiles(newOrder);
  };

  // 重新排序文件
  const handleReorderFiles = async (newOrder: string[]) => {
    try {
      await workspaceApi.setSystemPromptFiles(newOrder);
      setEnabledFiles(newOrder);
    } catch (error) {
      console.error("Failed to reorder files:", error);
      message.error(t("common.error"));
    }
  };

  // 复制内容
  const copyToClipboard = async () => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(fileContent);
        message.success(t("common.copied"));
      } else {
        const textArea = document.createElement("textarea");
        textArea.value = fileContent;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand("copy");
        textArea.remove();
        message.success(t("common.copied"));
      }
    } catch (err) {
      console.error("Failed to copy text: ", err);
      message.error(t("common.copyFailed"));
    }
  };

  // 下载工作区
  const handleDownload = async () => {
    try {
      const { blob, filename } = await workspaceApi.downloadWorkspace();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      message.success(t("workspace.downloadSuccess"));
    } catch (error) {
      console.error("Download failed:", error);
      message.error(t("workspace.downloadFailed"));
    }
  };

  // 上传文件到当前目录
  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await handleFileUploadToPath(file);
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className={styles.fileManagerPage}>
      <div className={styles.pageHeader}>
        <div>
          <div className={styles.pageTitle}>
            {t("config.files")}
          </div>
          {workspacePath && (
            <div className={styles.workspacePath}>
              {t("workspace.workspacePath")}: {workspacePath}
            </div>
          )}
        </div>
        <div className={styles.actionButtons}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            style={{ display: "none" }}
            accept="*"
            title={t("workspace.uploadFileTitle", "Select a file to upload")}
          />
          <Tooltip title={t("workspace.uploadTooltip")} placement="top">
            <Button
              size="small"
              onClick={handleUploadClick}
              icon={<UploadOutlined />}
              loading={uploading}
            >
              {t("common.upload")}
            </Button>
          </Tooltip>
          <Button
            size="small"
            onClick={handleDownload}
            icon={<DownloadOutlined />}
          >
            {t("common.download")}
          </Button>
        </div>
      </div>

      <div className={styles.content}>
        {/* 左侧：文件列表 */}
        <div className={styles.fileListPanel}>
          <Card
            bodyStyle={{
              padding: 16,
              display: "flex",
              flexDirection: "column",
              height: "100%",
              overflow: "auto",
            }}
            style={{ flex: 1, minHeight: 0 }}
          >
            {/* 面包屑导航 — 逐级可点击 */}
            <div className={styles.breadcrumb}>
              <span onClick={() => fetchDirectory("")} style={{ cursor: "pointer", color: "#1677ff" }}>
                workspace
              </span>
              {currentPath && (
                currentPath.split("/").map((segment, idx, arr) => (
                  <span key={idx}>
                    <span className={styles.separator}> / </span>
                    {idx === arr.length - 1 ? (
                      <span>{segment}</span>
                    ) : (
                      <span
                        onClick={() => fetchDirectory(arr.slice(0, idx + 1).join("/"))}
                        style={{ cursor: "pointer", color: "#1677ff" }}
                      >
                        {segment}
                      </span>
                    )}
                  </span>
                ))
              )}
            </div>

            {/* 预定义目录快捷入口 */}
            {currentPath === "" && (
              <div style={{ marginBottom: 8 }}>
                <div
                  className={styles.fileItem}
                  style={{ cursor: "pointer" }}
                  onClick={() => fetchDirectory("media")}
                >
                  <div className={styles.fileItemHeader}>
                    <div className={styles.fileInfo}>
                      <div className={styles.fileItemName}>
                        <FolderOutlined style={{ marginRight: 8, color: "#faad14" }} />
                        media/
                      </div>
                    </div>
                  </div>
                </div>
                <div
                  className={styles.fileItem}
                  style={{ cursor: "pointer", opacity: 0.6 }}
                  onClick={() => fetchDirectory("skills")}
                >
                  <div className={styles.fileItemHeader}>
                    <div className={styles.fileInfo}>
                      <div className={styles.fileItemName}>
                        <FolderOutlined style={{ marginRight: 8, color: "#faad14" }} />
                        skills/ (管理)
                      </div>
                    </div>
                  </div>
                </div>
                <div
                  className={styles.fileItem}
                  style={{ cursor: "pointer", opacity: 0.6 }}
                  onClick={() => fetchDirectory("memory")}
                >
                  <div className={styles.fileItemHeader}>
                    <div className={styles.fileInfo}>
                      <div className={styles.fileItemName}>
                        <FolderOutlined style={{ marginRight: 8, color: "#faad14" }} />
                        memory/ (管理)
                      </div>
                    </div>
                  </div>
                </div>
                <div style={{ margin: "8px 0", borderTop: "1px solid #f0f0f0" }} />
              </div>
            )}

            {/* 目录文件列表 */}
            <Spin spinning={loadingDir}>
              <div className={styles.scrollContainer} style={{ maxHeight: 240, marginBottom: 16 }}>
                {dirEntries.length > 0 ? (
                  dirEntries.map((entry) => (
                    <div
                      key={entry.name}
                      className={styles.fileItem}
                      style={{ cursor: entry.type === "dir" ? "pointer" : "default" }}
                      onClick={() => {
                        if (entry.type === "dir") handleEnterDir(entry);
                      }}
                      onDoubleClick={() => {
                        if (entry.type === "file" && entry.name.endsWith(".md")) {
                          handleFileClick({ filename: entry.name, path: currentPath ? `${currentPath}/${entry.name}` : entry.name, size: entry.size } as MarkdownFile);
                        }
                      }}
                    >
                      <div className={styles.fileItemHeader}>
                        <div className={styles.fileInfo}>
                          <div className={styles.fileItemName}>
                            {entry.type === "dir" ? (
                              <FolderOutlined style={{ marginRight: 8, color: "#faad14" }} />
                            ) : (
                              <FileOutlined style={{ marginRight: 8 }} />
                            )}
                            {entry.name}
                          </div>
                          <div className={styles.fileItemMeta}>
                            {entry.type === "file" ? formatFileSize(entry.size) : ""}
                          </div>
                        </div>
                        <div className={styles.fileItemActions}>
                          {entry.deletable && (
                            <Popconfirm
                              title={t("common.confirmDelete")}
                              onConfirm={(e) => { e?.stopPropagation(); handleDeleteFile(entry); }}
                              onCancel={(e) => e?.stopPropagation()}
                              okText={t("common.confirm")}
                              cancelText={t("common.cancel")}
                            >
                              <Button
                                size="small"
                                danger
                                icon={<DeleteOutlined />}
                                onClick={(e) => e.stopPropagation()}
                              />
                            </Popconfirm>
                          )}
                          {entry.type === "file" && (
                            <Tooltip title={t("common.download")}>
                              <Button
                                size="small"
                                icon={<DownloadOutlined />}
                                onClick={async (e) => {
                                  e.stopPropagation();
                                  const filePath = currentPath
                                    ? `${currentPath}/${entry.name}`
                                    : entry.name;
                                  const url = getApiUrl(`/webchat/agent/workspace/files/download?path=${encodeURIComponent(filePath)}`);
                                  try {
                                    const r = await fetch(url, { headers: getAuthHeaders() });
                                    if (!r.ok) throw new Error("Download failed");
                                    const blob = await r.blob();
                                    const blobUrl = URL.createObjectURL(blob);
                                    const a = document.createElement("a");
                                    a.href = blobUrl;
                                    a.download = entry.name;
                                    a.click();
                                    setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
                                  } catch {
                                    message.error(t("workspace.downloadFailed"));
                                  }
                                }}
                              />
                            </Tooltip>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className={styles.emptyState}>{t("workspace.emptyState")}</div>
                )}
              </div>
            </Spin>

            <div className={styles.divider} />

            <div className={styles.headerRow}>
              <h3 className={styles.sectionTitle}>{t("workspace.coreFiles")}</h3>
              <Button
                size="small"
                onClick={() => fetchFiles()}
                icon={<ReloadOutlined />}
              />
            </div>

            <p className={styles.infoText}>{t("workspace.coreFilesDesc")}</p>
            <div className={styles.divider} />

            <div className={styles.scrollContainer}>
              {files.length > 0 ? (
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleDragEnd}
                >
                  <SortableContext
                    items={enabledFiles}
                    strategy={verticalListSortingStrategy}
                  >
                    {files.map((file) => {
                      const isEnabled = enabledFiles.includes(file.filename);
                      return (
                        <SortableFileItem
                          key={file.filename}
                          file={file}
                          selectedFile={selectedFile}
                          expandedMemory={expandedMemory}
                          dailyMemories={dailyMemories}
                          enabled={isEnabled}
                          disabled={false}
                          onFileClick={handleFileClick}
                          onDailyMemoryClick={handleDailyMemoryClick}
                          onToggleEnabled={handleToggleFileEnabled}
                        />
                      );
                    })}
                  </SortableContext>
                </DndContext>
              ) : (
                <div className={styles.emptyState}>{t("workspace.noFiles")}</div>
              )}
            </div>
          </Card>
        </div>

        {/* 右侧：文件编辑器 */}
        <div className={styles.fileEditor}>
          <Card 
            className={styles.editorCard}
            bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}
          >
            {selectedFile ? (
              <>
                <div className={styles.editorHeader}>
                  <div>
                    <div className={styles.fileName}>{selectedFile.filename}</div>
                    <div className={styles.filePath}>{selectedFile.path}</div>
                  </div>
                  <div className={styles.buttonGroup}>
                    <Button
                      size="small"
                      onClick={handleReset}
                      disabled={!hasChanges}
                      icon={<UndoOutlined />}
                    >
                      {t("common.reset")}
                    </Button>
                    <Button
                      type="primary"
                      size="small"
                      onClick={handleSave}
                      disabled={!hasChanges}
                      loading={saving}
                      icon={<SaveOutlined />}
                    >
                      {t("common.save")}
                    </Button>
                  </div>
                </div>

                <div className={styles.editorContent}>
                <div className={styles.contentLabel}>
                  <div>{t("common.content")}</div>
                  {isMarkdownFile && (
                    <div className={styles.buttonGroup}>
                      <div className={styles.markdownToggle}>
                        <span className={styles.toggleLabel}>
                          {t("common.preview")}
                        </span>
                        <Switch
                          checked={showMarkdown}
                          onChange={setShowMarkdown}
                          size="small"
                        />
                      </div>
                      <Button
                        icon={<CopyOutlined />}
                        type="text"
                        onClick={copyToClipboard}
                        className={styles.copyButton}
                      />
                    </div>
                  )}
                </div>
                <Spin spinning={loadingFile}>
                  {showMarkdown && isMarkdownFile ? (
                    <XMarkdown
                      content={markdownContent}
                      className={styles.markdownViewer}
                    />
                  ) : (
                    <Input.TextArea
                      value={fileContent}
                      onChange={(e) => setFileContent(e.target.value)}
                      className={styles.textarea}
                      placeholder={t("workspace.fileContent")}
                    />
                  )}
                </Spin>
              </div>
            </>
          ) : (
            <div className={styles.emptyState}>{t("workspace.selectFile")}</div>
          )}
          <p className={styles.attribution}>{t("workspace.attribution")}</p>
          </Card>
        </div>
      </div>
    </div>
  );
}
