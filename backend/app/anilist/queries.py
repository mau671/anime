ANIME_SEARCH_QUERY = """
query ($page: Int, $perPage: Int, $season: MediaSeason, $seasonYear: Int, $status: MediaStatus) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      total
      perPage
      currentPage
      lastPage
      hasNextPage
    }
    media(season: $season, seasonYear: $seasonYear, status: $status, type: ANIME) {
      id
      title {
        romaji
        english
        native
      }
      format
      season
      seasonYear
      status
      genres
      synonyms
      description(asHtml: false)
      averageScore
      popularity
      coverImage {
        large
      }
      siteUrl
      updatedAt
    }
  }
}
"""

ANIME_BY_ID_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    title {
      romaji
      english
      native
    }
    format
    season
    seasonYear
    status
    genres
    synonyms
    description(asHtml: false)
    averageScore
    popularity
    coverImage {
      large
    }
    siteUrl
    updatedAt
  }
}
"""