import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import {
  getBackupDetail,
  getBackupProductionPolicy,
  listBackups,
  runBackupRestoreDrill,
} from "@/api/backups"
import BackupsPage from "./BackupsPage"

vi.mock("@/api/backups", () => ({
  getBackupDetail: vi.fn(),
  getBackupProductionPolicy: vi.fn(),
  listBackups: vi.fn(),
  runBackupRestoreDrill: vi.fn(),
}))

const backup = {
  id: "backup-1",
  name: "每日备份",
  description: "daily",
  created_at: "2026-05-16T00:00:00+00:00",
  version: "1",
  scope: {
    include_agents: true,
    include_global_config: true,
    include_secrets: false,
    include_skill_pool: true,
  },
  agent_count: 2,
  qwenpaw_version: "1.0.0",
  system_info: {},
}

describe("BackupsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(listBackups).mockResolvedValue([backup])
    vi.mocked(getBackupProductionPolicy).mockResolvedValue({
      schedule: "0 3 * * *",
      retention_days: 90,
      remote_store: "filesystem",
      integrity: "sha256",
    })
    vi.mocked(getBackupDetail).mockResolvedValue({
      ...backup,
      workspace_stats: {
        wx_acme: { files: 10, size: 2048 },
      },
    })
    vi.mocked(runBackupRestoreDrill).mockResolvedValue({
      ok: true,
      sandbox_dir: "D:/backups/_restore_drills/a",
    })
  })

  it("renders backup list, policy and staged risky operations", async () => {
    render(<BackupsPage />)

    expect(
      await screen.findByRole("heading", { name: "备份恢复" }),
    ).toBeInTheDocument()
    expect(screen.getByText("0 3 * * *")).toBeInTheDocument()
    expect(screen.getByText("每日备份")).toBeInTheDocument()
    expect(screen.getAllByText(/真实 restore、delete、import/).length).toBeGreaterThan(0)
    expect(
      screen.queryByRole("button", {
        name: /真实恢复|删除|导入|覆盖|restore|delete|import/i,
      }),
    ).not.toBeInTheDocument()
  })

  it("loads backup detail and runs restore drill", async () => {
    render(<BackupsPage />)

    await userEvent.click(await screen.findByRole("button", { name: /详.*情/ }))
    expect(await screen.findByText("Workspace Stats")).toBeInTheDocument()
    expect(screen.getByText(/wx_acme/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: /恢.*复.*演.*练/ }))

    await waitFor(() => {
      expect(runBackupRestoreDrill).toHaveBeenCalledWith("backup-1")
    })
  })
})
