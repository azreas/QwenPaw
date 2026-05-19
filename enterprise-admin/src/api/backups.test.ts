import { beforeEach, describe, expect, it, vi } from "vitest"
import { get, post } from "./http"
import {
  getBackupDetail,
  getBackupProductionPolicy,
  listBackups,
  runBackupRestoreDrill,
} from "./backups"

vi.mock("./http", () => ({
  get: vi.fn(),
  post: vi.fn(),
}))

describe("backups api", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(get).mockResolvedValue({})
    vi.mocked(post).mockResolvedValue({})
  })

  it("loads backup list, detail and production policy", async () => {
    await listBackups()
    await getBackupDetail("backup/a")
    await getBackupProductionPolicy()

    expect(get).toHaveBeenNthCalledWith(1, "/backups")
    expect(get).toHaveBeenNthCalledWith(2, "/backups/backup%2Fa")
    expect(get).toHaveBeenNthCalledWith(3, "/backups/production/policy")
  })

  it("runs restore drill using safe production endpoint", async () => {
    await runBackupRestoreDrill("backup/a")

    expect(post).toHaveBeenCalledWith("/backups/production/drill", {
      backup_id: "backup/a",
    })
  })
})
