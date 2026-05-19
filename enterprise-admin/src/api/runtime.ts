import { get, getRoot } from './http'
import type { VersionInfo, ReadyStatus, EnterpriseReadiness } from './types'

export async function getVersion(): Promise<VersionInfo> {
  return await get<VersionInfo>('/version')
}

export async function getReady(): Promise<ReadyStatus> {
  return await getRoot<ReadyStatus>('/ready')
}

export async function getEnterpriseReadiness(): Promise<EnterpriseReadiness> {
  return await get<EnterpriseReadiness>('/enterprise/readiness')
}
