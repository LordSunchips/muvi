import Foundation

struct MovieDetailDTO: Codable, Hashable, Identifiable {
    let id: Int
    let tmdbId: Int
    let title: String
    let year: Int?
    let posterPath: String?
    let genres: [GenreDTO]
    let addedAt: Date
    let score: Double?
    let bucket: Bucket?
    let rankings: [RankingDTO]

    enum CodingKeys: String, CodingKey {
        case id
        case tmdbId = "tmdb_id"
        case title
        case year
        case posterPath = "poster_path"
        case genres
        case addedAt = "added_at"
        case score
        case bucket
        case rankings
    }

    /// Adapter used when handing the movie off to RankFlowView (which takes LibraryMovieDTO).
    var asLibraryMovie: LibraryMovieDTO {
        LibraryMovieDTO(
            id: id,
            tmdbId: tmdbId,
            title: title,
            year: year,
            posterPath: posterPath,
            genres: genres,
            addedAt: addedAt,
            score: score,
            bucket: bucket,
            rankingCount: rankings.count
        )
    }
}
