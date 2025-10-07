export type MediaTitle = {
  english?: string | null
  romaji?: string | null
  native?: string | null
}

export type MediaCoverImage = {
  medium?: string | null
  large?: string | null
  extraLarge?: string | null
  color?: string | null
}

export type MediaDate = {
  year?: number | null
  month?: number | null
  day?: number | null
}

export type MediaNextAiringEpisode = {
  episode?: number | null
  airingAt?: number | null
}

export type Anime = {
  id?: number
  anilistId?: number
  anilist_id?: number
  title?: MediaTitle | null
  coverImage?: MediaCoverImage | null
  bannerImage?: string | null
  description?: string | null
  format?: string | null
  status?: string | null
  episodes?: number | null
  genres?: string[] | null
  synonyms?: string[] | null
  startDate?: MediaDate | null
  endDate?: MediaDate | null
  nextAiringEpisode?: MediaNextAiringEpisode | null
  season?: string | null
  seasonYear?: number | null
  averageScore?: number | null
  popularity?: number | null
  siteUrl?: string | null
  [key: string]: unknown
}

export type AnimeEnvelope = {
  anime: Anime
}

export type Settings = {
  anilist_id: number
  enabled?: boolean | null
  save_path?: string | null
  save_path_template?: string | null
  search_query?: string | null
  includes?: string[] | null
  excludes?: string[] | null
  preferred_resolution?: string | null
  preferred_subgroup?: string | null
  auto_query_from_synonyms?: boolean | null
  tvdb_id?: number | null
  tvdb_season?: number | null
  tmdb_id?: number | null
  tmdb_season?: number | null
  created_at?: string | null
  updated_at?: string | null
  [key: string]: unknown
}

export type TVDBMetadata = {
  id: number
  name?: string | null
  slug?: string | null
  status?: string | null
  overview?: string | null
  first_aired?: string | null
  year?: number | null
  image?: string | null
  network?: string | null
  runtime?: number | null
  season?: number | null
}

export type TMDBMetadata = {
  id: number
  type: "movie" | "tv"
  title?: string | null
  original_title?: string | null
  name?: string | null
  original_name?: string | null
  release_date?: string | null
  first_air_date?: string | null
  year?: number | null
  overview?: string | null
  poster_path?: string | null
  runtime?: number | null
  genres?: string[] | null
  season?: number | null
  season_name?: string | null
  season_overview?: string | null
  season_air_date?: string | null
  episode_count?: number | null
}

export type SettingsEnvelope = {
  settings: Settings
  anime?: Anime | null
  tvdb_metadata?: TVDBMetadata | null
  tmdb_metadata?: TMDBMetadata | null
}

export type SettingsUpdatePayload = {
  enabled?: boolean | null
  save_path?: string | null
  save_path_template?: string | null
  search_query?: string | null
  includes?: string[] | null
  excludes?: string[] | null
  preferred_resolution?: string | null
  preferred_subgroup?: string | null
  auto_query_from_synonyms?: boolean | null
  tvdb_id?: number | null
  tvdb_season?: number | null
  tmdb_id?: number | null
  tmdb_season?: number | null
}

export type PathMapping = {
  from: string
  to: string
}

export type AppConfig = {
  tvdb_api_key?: string | null
  tmdb_api_key?: string | null
  qbittorrent_enabled: boolean
  qbittorrent_url?: string | null
  qbittorrent_username?: string | null
  qbittorrent_password?: string | null
  qbittorrent_category: string
  qbittorrent_torrent_template?: string | null
  qbittorrent_save_template?: string | null
  path_mappings: PathMapping[]
  auto_add_to_qbittorrent: boolean
  default_save_path?: string | null
  default_save_path_template?: string | null
  default_search_query_template?: string | null
  default_preferred_resolution?: string | null
  default_preferred_subgroup?: string | null
  default_auto_query_from_synonyms: boolean
  created_at?: string | null
  updated_at?: string | null
}

export type AppConfigPayload = Partial<
  Omit<
    AppConfig,
    | "created_at"
    | "updated_at"
    | "path_mappings"
    | "qbittorrent_enabled"
    | "auto_add_to_qbittorrent"
    | "qbittorrent_category"
  >
> & {
  qbittorrent_enabled?: boolean | null
  auto_add_to_qbittorrent?: boolean | null
  qbittorrent_category?: string | null
  path_mappings?: PathMapping[] | null
}

export type ScanNyaaJob = {
  job_type: "scan_nyaa"
}

export type InitDbJob = {
  job_type: "init_db"
}

export type SyncAnilistJob = {
  job_type: "sync_anilist"
  season?: "WINTER" | "SPRING" | "SUMMER" | "FALL" | null
  season_year?: number | null
}

export type ExportQbittorrentJob = {
  job_type: "export_qbittorrent"
  limit?: number
  anilist_id?: number | null
  items?: string[]
}

export type JobRunPayload =
  | ScanNyaaJob
  | SyncAnilistJob
  | InitDbJob
  | ExportQbittorrentJob

export type JobExecutionResponse = {
  status: "ok" | "completed" | "queued" | "failed"
  detail?: string | null
  task_id: string
  result?: Record<string, unknown> | null
}

export type JobHistoryEntry = {
  id?: string | null
  task_id: string
  task_type: string
  status: string
  trigger: string
  started_at?: string | null
  completed_at?: string | null
  parameters?: Record<string, unknown>
  result?: Record<string, unknown>
  error?: string | null
  items_processed?: number
  items_succeeded?: number
  items_failed?: number
  anilist_id?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export type JobHistoryFilters = {
  job_type?: string | null
  status?: string | null
  anilist_id?: number | null
}

export type JobHistoryListResponse = {
  tasks: JobHistoryEntry[]
  count: number
  limit: number
  filters?: JobHistoryFilters
}

export type RunningJobsResponse = {
  tasks: JobHistoryEntry[]
  count: number
}

export type JobStatusAggregate = {
  status: string
  count: number
  total_processed?: number
  total_succeeded?: number
  total_failed?: number
}

export type JobStatisticsResponse = {
  period: "24h" | "7d" | "30d" | "all"
  job_type?: string | null
  statistics: JobStatusAggregate[]
}

export type JobTypeInfo = {
  type: string
  description: string
  trigger_types: string[]
}

export type JobTypeListResponse = {
  job_types: JobTypeInfo[]
}

export type QBittorrentHistoryRecord = {
  id?: string | null
  anilist_id: number
  title: string
  torrent_path: string
  save_path: string
  category?: string | null
  infohash?: string | null
  qbittorrent_response?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type QBittorrentHistoryListResponse = {
  anilist_id: number
  count: number
  records: QBittorrentHistoryRecord[]
  limit: number
}

export type TaskStatusResponse = {
  status: "ok" | "completed" | "queued" | "failed"
  detail?: string | null
}

export type TorrentSeenRecord = {
  id?: string | null
  title: string
  link: string
  source?: string | null
  magnet?: string | null
  infohash?: string | null
  saved_at?: string | null
  published_at?: string | null
}

export type ApiError = {
  detail?: unknown
  message?: string
}


