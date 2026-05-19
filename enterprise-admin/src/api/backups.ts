import { get, post } from "./http"
import type {
  BackupDetail,
  BackupDrillResult,
  BackupMeta,
  BackupProductionPolicy,
} from "./types"

export function listBackups(): Promise<BackupMeta[]> {
  return get<BackupMeta[]>("/backups")
}

export function getBackupDetail(backupId: string): Promise<BackupDetail> {
  return get<BackupDetail>(`/backups/${encodeURIComponent(backupId)}`)
}

export function getBackupProductionPolicy(): Promise<BackupProductionPolicy> {
  return get<BackupProductionPolicy>("/backups/production/policy")
}

export function runBackupRestoreDrill(
  backupId: string,
): Promise<BackupDrillResult> {
  return post<BackupDrillResult>("/backups/production/drill", {
    backup_id: backupId,
  })
}
