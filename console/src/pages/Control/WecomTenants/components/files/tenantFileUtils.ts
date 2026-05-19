import type { WecomTenantFileInfo } from "../../../../../api/types";

export type FileScope = "files" | "memory";

export function isSafeFileName(filename: string): boolean {
  return /^[\w.-]+\.(md|json)$/i.test(filename);
}

export function defaultFileContent(filename: string): string {
  return filename.toLowerCase().endsWith(".json") ? "{}\n" : "";
}

export function isJsonFile(filename: string | null): boolean {
  return !!filename && filename.toLowerCase().endsWith(".json");
}

export function pickTenantFile(
  scope: FileScope,
  files: WecomTenantFileInfo[],
  memory: WecomTenantFileInfo[],
  current: string | null,
): string | null {
  const list = scope === "files" ? files : memory;
  return current && list.some((file) => file.filename === current)
    ? current
    : list[0]?.filename || null;
}
