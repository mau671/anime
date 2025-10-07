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

export type TaskHistoryEntry = {
  id?: string
  task_id?: string
  task_type?: string | null
  status?: string | null
  detail?: string | null
  started_at?: string | null
  finished_at?: string | null
  created_at?: string | null
  updated_at?: string | null
  anilist_id?: number | null
  [key: string]: unknown
}

export type TaskHistoryResponse = {
  items?: TaskHistoryEntry[]
  results?: TaskHistoryEntry[]
  data?: TaskHistoryEntry[]
  total?: number
  [key: string]: unknown
}

export type RunningTasksResponse = {
  items?: TaskHistoryEntry[]
  data?: TaskHistoryEntry[]
  [key: string]: unknown
}

export type TaskStatisticsResponse = {
  [key: string]: unknown
}

export type TaskTypesResponse = (string | { value?: string; label?: string })[] | {
  items?: (string | { value?: string; label?: string })[]
  [key: string]: unknown
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

export type TaskStatusResponse = {
  status: "ok" | "completed" | "queued" | "failed"
  detail?: string | null
}

export type SyncAnilistRequest = {
  season?: "WINTER" | "SPRING" | "SUMMER" | "FALL" | null
  season_year?: number | null
}

export type SyncAnilistResponse = {
  status: "ok" | "completed" | "queued" | "failed"
  detail?: string | null
  count: number
  season: "WINTER" | "SPRING" | "SUMMER" | "FALL"
  season_year: number
}

export type ScanNyaaResponse = {
  status?: "completed" | "queued" | "ok"
  detail?: string | null
}

export type ApiError = {
  detail?: unknown
  message?: string
}


