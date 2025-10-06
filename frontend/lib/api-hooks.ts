"use client"

import useSWR, { mutate } from "swr"

import { apiFetch } from "@/lib/api-client"
import type {
  AnimeEnvelope,
  SettingsEnvelope,
  SettingsUpdatePayload,
  SyncAnilistRequest,
  SyncAnilistResponse,
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
} as const

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


