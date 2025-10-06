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
