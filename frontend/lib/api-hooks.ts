"use client"

import useSWR, { mutate } from "swr"

import { apiFetch } from "@/lib/api-client"
import type {
  AnimeEnvelope,
  AppConfig,
  AppConfigPayload,
  ExportQbittorrentJob,
  InitDbJob,
  JobExecutionResponse,
  JobHistoryEntry,
  JobHistoryFilters,
  JobHistoryListResponse,
  JobRunPayload,
  JobStatisticsResponse,
  JobTypeListResponse,
  RunningJobsResponse,
  ScanNyaaJob,
  SettingsEnvelope,
  SettingsUpdatePayload,
  SyncAnilistJob,
  TaskStatusResponse,
  TorrentSeenRecord,
} from "@/lib/api-types"

const CACHE_KEYS = {
  animes: (limit?: number) => ["animes", limit ?? 50],
  settings: () => ["settings"],
  animeSettings: (anilistId: number) => ["settings", anilistId],
  downloads: (anilistId: number, limit?: number) => [
    "downloads",
    anilistId,
    limit ?? 50,
  ],
  appConfig: () => ["app-config"],
  jobHistory: (filters?: JobHistoryFilters & { limit?: number }) => [
    "job-history",
    filters ?? {},
  ],
  runningJobs: () => ["running-jobs"],
  jobStatistics: (filters?: { job_type?: string | null; period?: "24h" | "7d" | "30d" | "all" }) => [
    "job-stats",
    filters ?? {},
  ],
  jobTypes: () => ["job-types"],
}

export function useAnimes(limit = 50) {
  return useSWR(CACHE_KEYS.animes(limit), async () => {
    const data = await apiFetch<AnimeEnvelope[]>(`/animes?limit=${limit}`)
    return data
  })
}

export function useSettings() {
  return useSWR(CACHE_KEYS.settings(), async () => {
    const data = await apiFetch<SettingsEnvelope[]>(`/settings`)
    return data
  })
}

export const GLOBAL_SETTINGS_ID = 0

export function useAnimeSettings(anilistId: number | null) {
  return useSWR(
    anilistId !== null ? CACHE_KEYS.animeSettings(anilistId) : null,
    async () => {
      const data = await apiFetch<SettingsEnvelope>(`/settings/${anilistId}`)
      return data
    }
  )
}

export function useGlobalSettings() {
  return useAnimeSettings(GLOBAL_SETTINGS_ID)
}

export function useDownloadHistory(anilistId: number | null, limit = 50) {
  return useSWR(
    anilistId ? CACHE_KEYS.downloads(anilistId, limit) : null,
    async () => {
      const data = await apiFetch<TorrentSeenRecord[]>(
        `/settings/${anilistId}/downloads?limit=${limit}`
      )
      return data
    }
  )
}

export async function updateAnimeSettings(
  anilistId: number,
  payload: SettingsUpdatePayload
) {
  const data = await apiFetch<SettingsEnvelope>(`/settings/${anilistId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  })

  await Promise.all([
    mutate(CACHE_KEYS.animeSettings(anilistId)),
    mutate(CACHE_KEYS.settings()),
  ])

  return data
}

export async function updateGlobalSettings(payload: SettingsUpdatePayload) {
  return updateAnimeSettings(GLOBAL_SETTINGS_ID, payload)
}

export async function deleteAnimeSettings(anilistId: number) {
  const data = await apiFetch<TaskStatusResponse>(`/settings/${anilistId}`, {
    method: "DELETE",
  })

  await Promise.all([
    mutate(CACHE_KEYS.animeSettings(anilistId)),
    mutate(CACHE_KEYS.settings()),
    mutate(CACHE_KEYS.animes()),
  ])

  return data
}

export async function reloadScheduler() {
  return apiFetch<TaskStatusResponse>("/scheduler/reload", {
    method: "POST",
  })
}

export function useHealth() {
  return useSWR(["health"], async () => {
    const data = await apiFetch<TaskStatusResponse>("/health")
    return data
  })
}

export function useAppConfig() {
  return useSWR(CACHE_KEYS.appConfig(), async () => {
    const data = await apiFetch<AppConfig>("/config/")
    return data
  })
}

export async function updateAppConfig(payload: AppConfigPayload) {
  const data = await apiFetch<AppConfig>("/config/", {
    method: "PUT",
    body: JSON.stringify(payload),
  })

  await mutate(CACHE_KEYS.appConfig())
  return data
}

export async function testQbittorrentConnection() {
  return apiFetch<Record<string, string>>("/config/test-qbittorrent", {
    method: "POST",
  })
}

export function useJobHistory(filters?: JobHistoryFilters & { limit?: number }) {
  return useSWR(CACHE_KEYS.jobHistory(filters), async () => {
    const params = new URLSearchParams()
    if (filters?.limit) params.set("limit", filters.limit.toString())
    if (filters?.job_type) params.set("job_type", filters.job_type)
    if (filters?.status) params.set("status", filters.status)
    if (typeof filters?.anilist_id === "number") {
      params.set("anilist_id", filters.anilist_id.toString())
    }

    const query = params.toString()
    const data = await apiFetch<JobHistoryListResponse>(
      query ? `/jobs/history?${query}` : "/jobs/history"
    )

    return {
      ...data,
      tasks: data.tasks ?? [],
    }
  })
}

export function useRunningJobs() {
  return useSWR(CACHE_KEYS.runningJobs(), async () => {
    const data = await apiFetch<RunningJobsResponse>("/jobs/history/running")
    return data.tasks ?? []
  })
}

export function useJobStatistics(filters?: { job_type?: string | null; period?: "24h" | "7d" | "30d" | "all" }) {
  return useSWR(CACHE_KEYS.jobStatistics(filters), async () => {
    const params = new URLSearchParams()
    if (filters?.job_type) params.set("job_type", filters.job_type)
    if (filters?.period) params.set("period", filters.period)

    const query = params.toString()
    const data = await apiFetch<JobStatisticsResponse>(
      query ? `/jobs/history/statistics/summary?${query}` : "/jobs/history/statistics/summary"
    )
    return data
  })
}

export function useJobTypes() {
  return useSWR(CACHE_KEYS.jobTypes(), async () => {
    const data = await apiFetch<JobTypeListResponse>("/jobs/types")
    return data.job_types ?? []
  })
}

export async function runJob(payload: JobRunPayload) {
  const data = await apiFetch<JobExecutionResponse>("/jobs/run", {
    method: "POST",
    body: JSON.stringify(payload),
  })

  await Promise.all([
    mutate(CACHE_KEYS.jobHistory()),
    mutate(CACHE_KEYS.runningJobs()),
    mutate(CACHE_KEYS.jobStatistics()),
  ])

  return data
}

export async function runScanNyaaJob() {
  return runJob({ job_type: "scan_nyaa" } satisfies ScanNyaaJob)
}

export async function runInitDbJob() {
  return runJob({ job_type: "init_db" } satisfies InitDbJob)
}

export async function runSyncAnilistJob(payload: Omit<SyncAnilistJob, "job_type"> = {}) {
  return runJob({ job_type: "sync_anilist", ...payload } satisfies SyncAnilistJob)
}

export async function runExportQbittorrentJob(payload: Omit<ExportQbittorrentJob, "job_type">) {
  return runJob({ job_type: "export_qbittorrent", ...payload } satisfies ExportQbittorrentJob)
}

export function useJobDetails(taskId: string | null) {
  return useSWR(taskId ? ["job-details", taskId] : null, async () => {
    if (!taskId) return null
    const data = await apiFetch<JobHistoryEntry>(`/jobs/history/${taskId}`)
    return data
  })
}


