import { useEffect, useMemo, useState } from "react";
import { Alert, Empty } from "@agentscope-ai/design";
import { Button, Card, Input, Modal } from "@agentscope-ai/design";
import { useTranslation } from "react-i18next";
import { wecomTenantApi } from "../../../../api/modules/wecomTenant";
import type { WecomTenantFileInfo } from "../../../../api/types";
import { useAppMessage } from "../../../../hooks/useAppMessage";
import styles from "../index.module.less";
import { CreateTenantFileModal } from "./files/CreateTenantFileModal";
import {
  defaultFileContent,
  isJsonFile,
  isSafeFileName,
  pickTenantFile,
  type FileScope,
} from "./files/tenantFileUtils";

interface Props {
  agentId: string;
}

export function TenantFilesMemoryTab({ agentId }: Props) {
  const { t } = useTranslation();
  const { message } = useAppMessage();
  const [scope, setScope] = useState<FileScope>("files");
  const [workspaceFiles, setWorkspaceFiles] = useState<WecomTenantFileInfo[]>([]);
  const [memoryFiles, setMemoryFiles] = useState<WecomTenantFileInfo[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [savedContent, setSavedContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newFilename, setNewFilename] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);

  const currentFiles = useMemo(
    () => (scope === "files" ? workspaceFiles : memoryFiles),
    [memoryFiles, scope, workspaceFiles],
  );
  const selectedInfo = useMemo(
    () => currentFiles.find((file) => file.filename === selected) || null,
    [currentFiles, selected],
  );
  const dirty = selected !== null && content !== savedContent;

  const confirmDiscard = (action: () => void | Promise<void>) => {
    if (!dirty) {
      void action();
      return;
    }
    Modal.confirm({
      title: t("wecomTenants.unsavedChangesTitle"),
      content: t("wecomTenants.unsavedChangesContent"),
      okText: t("wecomTenants.discardChanges"),
      cancelText: t("common.cancel"),
      onOk: action,
    });
  };

  const loadLists = async () => {
    setLoading(true);
    try {
      const [files, memory] = await Promise.all([
        wecomTenantApi.listWecomTenantFiles(agentId),
        wecomTenantApi.listWecomTenantMemory(agentId),
      ]);
      setWorkspaceFiles(files.files || []);
      setMemoryFiles(memory.files || []);
      setSelected(pickTenantFile(scope, files.files || [], memory.files || [], selected));
    } finally {
      setLoading(false);
    }
  };

  const loadContent = async (nextScope: FileScope, filename: string) => {
    setLoading(true);
    try {
      const file =
        nextScope === "files"
          ? await wecomTenantApi.getWecomTenantFile(agentId, filename)
          : await wecomTenantApi.getWecomTenantMemoryFile(agentId, filename);
      setContent(file.content);
      setSavedContent(file.content);
      setValidationError(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLists();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]);

  useEffect(() => {
    if (selected) loadContent(scope, selected);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId, scope, selected]);

  useEffect(() => {
    const blockUnload = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", blockUnload);
    return () => window.removeEventListener("beforeunload", blockUnload);
  }, [dirty]);

  const handleSave = async () => {
    if (!selected) return;
    if (isJsonFile(selected)) {
      try {
        JSON.parse(content || "{}");
      } catch (error) {
        setValidationError((error as Error).message);
        return;
      }
    }
    setSaving(true);
    try {
      if (scope === "files") {
        await wecomTenantApi.updateWecomTenantFile(agentId, selected, content);
      } else {
        await wecomTenantApi.updateWecomTenantMemoryFile(agentId, selected, content);
      }
      setSavedContent(content);
      setValidationError(null);
      message.success(t("wecomTenants.fileSavedReloaded"));
      await loadLists();
    } finally {
      setSaving(false);
    }
  };

  const switchScope = (nextScope: FileScope) => {
    confirmDiscard(() => {
      setScope(nextScope);
      setSelected(pickTenantFile(nextScope, workspaceFiles, memoryFiles, selected));
    });
  };

  const selectFile = (filename: string) => {
    confirmDiscard(() => setSelected(filename));
  };

  const createFile = async () => {
    const filename = newFilename.trim();
    if (!isSafeFileName(filename)) {
      setCreateError(t("wecomTenants.invalidFileName"));
      return;
    }
    setCreateError(null);
    setCreating(true);
    try {
      const nextContent = defaultFileContent(filename);
      if (scope === "files") {
        await wecomTenantApi.updateWecomTenantFile(agentId, filename, nextContent);
      } else {
        await wecomTenantApi.updateWecomTenantMemoryFile(
          agentId,
          filename,
          nextContent,
        );
      }
      setCreateOpen(false);
      setNewFilename("");
      await loadLists();
      setSelected(filename);
      setContent(nextContent);
      setSavedContent(nextContent);
      message.success(t("wecomTenants.fileSavedReloaded"));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = () => {
    if (!selected || scope !== "memory") return;
    Modal.confirm({
      title: t("wecomTenants.deleteMemoryTitle"),
      content: t("wecomTenants.deleteMemoryContent", { filename: selected }),
      okText: t("common.delete"),
      okType: "danger",
      cancelText: t("common.cancel"),
      onOk: async () => {
        await wecomTenantApi.deleteWecomTenantMemoryFile(agentId, selected);
        setSelected(null);
        setContent("");
        setSavedContent("");
        await loadLists();
      },
    });
  };

  return (
    <div className={styles.fileWorkspace}>
      <aside className={styles.fileList}>
        <div className={styles.segmented}>
          <button
            type="button"
            className={scope === "files" ? styles.segmentActive : ""}
            onClick={() => switchScope("files")}
          >
            {t("wecomTenants.workspaceFiles")}
          </button>
          <button
            type="button"
            className={scope === "memory" ? styles.segmentActive : ""}
            onClick={() => switchScope("memory")}
          >
            {t("wecomTenants.memoryFiles")}
          </button>
        </div>
        <Button block onClick={() => confirmDiscard(() => setCreateOpen(true))}>
          {t("wecomTenants.createFile")}
        </Button>
        {currentFiles.length ? (
          <div className={styles.fileItems}>
            {currentFiles.map((file) => (
              <button
                type="button"
                key={file.filename}
                className={selected === file.filename ? styles.fileActive : ""}
                onClick={() => selectFile(file.filename)}
              >
                <strong>{file.filename}</strong>
                <span>{file.size} B</span>
              </button>
            ))}
          </div>
        ) : (
          <Empty description={t("wecomTenants.noFiles")} />
        )}
      </aside>
      <Card
        className={styles.editorCard}
        title={
          <div className={styles.editorTitle}>
            <span>{selected || t("wecomTenants.noFileSelected")}</span>
            {dirty && <span>{t("wecomTenants.unsaved")}</span>}
          </div>
        }
        extra={
          <div className={styles.rowActions}>
            {scope === "memory" && selected && (
              <Button danger onClick={handleDelete}>
                {t("common.delete")}
              </Button>
            )}
            <Button
              type="primary"
              loading={saving}
              disabled={!selected}
              onClick={handleSave}
            >
              {t("common.save")}
            </Button>
          </div>
        }
      >
        {validationError && (
          <Alert
            className={styles.inlineAlert}
            type="error"
            showIcon
            message={t("wecomTenants.jsonInvalid")}
            description={validationError}
          />
        )}
        {selected && (
          <div className={styles.editorMeta}>
            <span>
              {t("wecomTenants.fileCharacters", { count: content.length })}
            </span>
            <span>
              {t("wecomTenants.updatedAt")}: {selectedInfo?.updated_at || "-"}
            </span>
          </div>
        )}
        <Input.TextArea
          value={content}
          disabled={!selected || loading}
          onChange={(event) => setContent(event.target.value)}
          autoSize={{ minRows: 18, maxRows: 28 }}
        />
      </Card>
      <CreateTenantFileModal
        open={createOpen} filename={newFilename}
        error={createError} creating={creating}
        onChange={setNewFilename}
        onCancel={() => setCreateOpen(false)}
        onCreate={createFile}
      />
    </div>
  );
}
