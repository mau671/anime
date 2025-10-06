import type { Anime, SettingsEnvelope, TVDBMetadata, TMDBMetadata } from "./api-types"

export type TemplateVariables = {
  // Date/Time variables
  currentYear: string
  currentMonth: string
  currentDay: string

  // Anime variables
  "anime.title.romaji": string
  "anime.title.english": string
  "anime.title.native": string
  "anime.season": string
  "anime.seasonYear": string
  "anime.format": string
  "anime.status": string
  "anime.anilistId": string

  // TVDB variables
  "tvdb.id": string
  "tvdb.name": string
  "tvdb.slug": string
  "tvdb.year": string
  "tvdb.season": string
  "tvdb.seasonNumber": string

  // TMDB variables
  "tmdb.id": string
  "tmdb.type": string
  "tmdb.title": string
  "tmdb.name": string
  "tmdb.year": string
  "tmdb.season": string
  "tmdb.seasonNumber": string
}

function sanitizePath(value: string): string {
  // Remove or replace invalid path characters
  return value
    .replace(/[<>:"|?*]/g, "")
    .replace(/\//g, "-")
    .replace(/\\/g, "-")
    .trim()
}

export function buildTemplateVariables(
  envelope: SettingsEnvelope
): Partial<TemplateVariables> {
  const anime = envelope.anime
  const tvdb = envelope.tvdb_metadata
  const tmdb = envelope.tmdb_metadata
  const settings = envelope.settings

  const now = new Date()
  
  // Season mapping
  const seasonMap: Record<string, string> = {
    WINTER: "winter",
    SPRING: "spring",
    SUMMER: "summer",
    FALL: "fall",
  }

  const variables: Partial<TemplateVariables> = {
    // Date/Time
    currentYear: now.getFullYear().toString(),
    currentMonth: (now.getMonth() + 1).toString().padStart(2, "0"),
    currentDay: now.getDate().toString().padStart(2, "0"),
  }

  // Anime variables
  if (anime) {
    if (anime.title?.romaji) {
      variables["anime.title.romaji"] = sanitizePath(anime.title.romaji)
    }
    if (anime.title?.english) {
      variables["anime.title.english"] = sanitizePath(anime.title.english)
    }
    if (anime.title?.native) {
      variables["anime.title.native"] = sanitizePath(anime.title.native)
    }
    if (anime.season) {
      variables["anime.season"] = seasonMap[anime.season.toUpperCase()] || anime.season.toLowerCase()
    }
    if (anime.seasonYear) {
      variables["anime.seasonYear"] = anime.seasonYear.toString()
    }
    if (anime.format) {
      variables["anime.format"] = sanitizePath(anime.format)
    }
    if (anime.status) {
      variables["anime.status"] = sanitizePath(anime.status)
    }
    const anilistId = anime.anilist_id ?? anime.anilistId
    if (anilistId) {
      variables["anime.anilistId"] = anilistId.toString()
    }
  }

  // TVDB variables
  if (tvdb) {
    variables["tvdb.id"] = tvdb.id.toString()
    if (tvdb.name) {
      variables["tvdb.name"] = sanitizePath(tvdb.name)
    }
    if (tvdb.slug) {
      variables["tvdb.slug"] = sanitizePath(tvdb.slug)
    }
    if (tvdb.year) {
      variables["tvdb.year"] = tvdb.year.toString()
    }
    if (tvdb.season !== null && tvdb.season !== undefined) {
      variables["tvdb.season"] = tvdb.season.toString()
    }
  }
  
  // Use configured season number if available
  if (settings.tvdb_season !== null && settings.tvdb_season !== undefined) {
    variables["tvdb.seasonNumber"] = settings.tvdb_season.toString().padStart(2, "0")
  }

  // TMDB variables
  if (tmdb) {
    variables["tmdb.id"] = tmdb.id.toString()
    variables["tmdb.type"] = tmdb.type
    
    const tmdbTitle = tmdb.title || tmdb.name
    if (tmdbTitle) {
      variables["tmdb.title"] = sanitizePath(tmdbTitle)
      variables["tmdb.name"] = sanitizePath(tmdbTitle)
    }
    
    if (tmdb.year) {
      variables["tmdb.year"] = tmdb.year.toString()
    }
    if (tmdb.season !== null && tmdb.season !== undefined) {
      variables["tmdb.season"] = tmdb.season.toString()
    }
  }
  
  // Use configured season number if available
  if (settings.tmdb_season !== null && settings.tmdb_season !== undefined) {
    variables["tmdb.seasonNumber"] = settings.tmdb_season.toString().padStart(2, "0")
  }

  return variables
}

export function applyTemplate(
  template: string,
  variables: Partial<TemplateVariables>
): string {
  let result = template

  // Replace all variables in the template
  Object.entries(variables).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      const regex = new RegExp(`\\{${key}\\}`, "g")
      result = result.replace(regex, value)
    }
  })

  return result
}

export function processPathTemplate(
  template: string,
  envelope: SettingsEnvelope
): string {
  const variables = buildTemplateVariables(envelope)
  return applyTemplate(template, variables)
}

export const TEMPLATE_EXAMPLES = [
  "/storage/data/torrents/shows/Anime Ongoing/{currentYear}/{anime.season}/{tvdb.name} ({tvdb.year}) [tvdbid-{tvdb.id}]/Season {tvdb.seasonNumber}",
  "/anime/{anime.seasonYear}/{anime.season}/{anime.title.english}",
  "/downloads/{tvdb.name}/S{tvdb.seasonNumber}",
  "/media/anime/{currentYear}/{anime.title.romaji}",
  "/torrents/{tmdb.type}/{tmdb.name} ({tmdb.year})/Season {tmdb.seasonNumber}",
]

export const AVAILABLE_VARIABLES: Array<{ key: keyof TemplateVariables; description: string }> = [
  { key: "currentYear", description: "Año actual" },
  { key: "currentMonth", description: "Mes actual (01-12)" },
  { key: "currentDay", description: "Día actual (01-31)" },
  { key: "anime.title.romaji", description: "Título en romaji" },
  { key: "anime.title.english", description: "Título en inglés" },
  { key: "anime.title.native", description: "Título nativo" },
  { key: "anime.season", description: "Temporada (winter, spring, summer, fall)" },
  { key: "anime.seasonYear", description: "Año de la temporada" },
  { key: "anime.format", description: "Formato del anime" },
  { key: "anime.status", description: "Estado del anime" },
  { key: "anime.anilistId", description: "ID de AniList" },
  { key: "tvdb.id", description: "ID de TVDB" },
  { key: "tvdb.name", description: "Nombre en TVDB" },
  { key: "tvdb.slug", description: "Slug de TVDB" },
  { key: "tvdb.year", description: "Año en TVDB" },
  { key: "tvdb.season", description: "Temporada en TVDB" },
  { key: "tvdb.seasonNumber", description: "Número de temporada configurado (TVDB)" },
  { key: "tmdb.id", description: "ID de TMDB" },
  { key: "tmdb.type", description: "Tipo en TMDB (movie/tv)" },
  { key: "tmdb.title", description: "Título en TMDB" },
  { key: "tmdb.name", description: "Nombre en TMDB" },
  { key: "tmdb.year", description: "Año en TMDB" },
  { key: "tmdb.season", description: "Temporada en TMDB" },
  { key: "tmdb.seasonNumber", description: "Número de temporada configurado (TMDB)" },
]

