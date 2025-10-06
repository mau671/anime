"use client"

import useSWR, { mutate } from "swr"

import { apiFetch } from "@/lib/api-client"
import type {
  AnimeEnvelope,
  AppConfig,
  AppConfigPayload,
  SettingsEnvelope,
  SettingsUpdatePayload,
  SyncAnilistRequest,
  SyncAnilistResponse,
  RunningTasksResponse,
  TaskHistoryEntry,
  TaskHistoryResponse,
  TaskStatisticsResponse,
  TaskStatusResponse,
  TaskTypesResponse,
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
  taskHistory: (filters?: TaskHistoryFilters) => ["task-history", filters ?? {}],
  runningTasks: () => ["task-running"],
  taskStatistics: (filters?: TaskStatisticsFilters) => ["task-stats", filters ?? {}],
  taskTypes: () => ["task-types"],
} as const

type TaskHistoryFilters = {
  limit?: number
  task_type?: string | null
  status?: string | null
  anilist_id?: number | null
}

type TaskStatisticsFilters = {
  task_type?: string | null
  period?: "24h" | "7d" | "30d" | "all"
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

export async function triggerScan() {
  return apiFetch<TaskStatusResponse>("/tasks/scan-nyaa", {
    method: "POST",
  })
}

export async function reloadScheduler() {
  return apiFetch<TaskStatusResponse>("/scheduler/reload", {
    method: "POST",
  })
}

export async function syncAnilist(payload: SyncAnilistRequest) {
  return apiFetch<SyncAnilistResponse>("/tasks/sync-anilist", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function initDatabase() {
  return apiFetch<TaskStatusResponse>("/tasks/init-db", {
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

export function useTaskHistory(filters?: TaskHistoryFilters) {
  return useSWR(CACHE_KEYS.taskHistory(filters), async () => {
    const params = new URLSearchParams()
    if (filters?.limit) params.set("limit", filters.limit.toString())
    if (filters?.task_type) params.set("task_type", filters.task_type)
    if (filters?.status) params.set("status", filters.status)
    if (typeof filters?.anilist_id === "number") {
      params.set("anilist_id", filters.anilist_id.toString())
    }

    const query = params.toString()
    const data = await apiFetch<TaskHistoryResponse>(
      query ? `/tasks/history/?${query}` : "/tasks/history/"
    )

    const items =
      data.items ?? data.results ?? data.data ?? (Array.isArray(data) ? data : [])

    return { ...data, items } as TaskHistoryResponse & { items: TaskHistoryEntry[] }
  })
}

export function useRunningTasks() {
  return useSWR(CACHE_KEYS.runningTasks(), async () => {
    const data = await apiFetch<RunningTasksResponse | TaskHistoryEntry[]>(
      "/tasks/history/running/list"
    )

    if (Array.isArray(data)) {
      return data
    }

    return data.items ?? data.data ?? []
  })
}

export function useTaskStatistics(filters?: TaskStatisticsFilters) {
  return useSWR(CACHE_KEYS.taskStatistics(filters), async () => {
    const params = new URLSearchParams()
    if (filters?.task_type) params.set("task_type", filters.task_type)
    if (filters?.period) params.set("period", filters.period)

    const query = params.toString()
    const data = await apiFetch<TaskStatisticsResponse>(
      query
        ? `/tasks/history/statistics/summary?${query}`
        : "/tasks/history/statistics/summary"
    )

    return data
  })
}

export function useTaskTypes() {
  return useSWR(CACHE_KEYS.taskTypes(), async () => {
    const data = await apiFetch<TaskTypesResponse>("/tasks/history/types/list")

    if (Array.isArray(data)) {
      return data
    }

    return data.items ?? []
  })
}

export function useTaskDetails(taskId: string | null) {
  return useSWR(taskId ? ["task-details", taskId] : null, async () => {
    if (!taskId) return null
    const data = await apiFetch<TaskHistoryEntry>(`/tasks/history/${taskId}`)
    return data
  })
}


