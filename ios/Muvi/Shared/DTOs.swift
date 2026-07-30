import Foundation

enum Bucket: String, Codable, CaseIterable, Identifiable, Hashable {
    case loved, fine, bad

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .loved: return "Loved"
        case .fine: return "Fine"
        case .bad: return "Bad"
        }
    }
}

enum DisplayMetric: String, Codable, CaseIterable, Identifiable {
    case latest, mean, median

    var id: String { rawValue }
    var displayName: String { rawValue.capitalized }
}

struct GenreDTO: Codable, Hashable, Identifiable {
    let id: Int
    let name: String
}

struct LibraryMovieDTO: Codable, Identifiable, Hashable {
    let id: Int
    let tmdbId: Int
    let title: String
    let year: Int?
    let posterPath: String?
    let genres: [GenreDTO]
    let addedAt: Date
    let score: Double?
    let bucket: Bucket?
    let rankingCount: Int

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
        case rankingCount = "ranking_count"
    }
}

struct TMDBSearchResultDTO: Codable, Identifiable, Hashable {
    let tmdbId: Int
    let title: String
    let year: Int?
    let posterPath: String?
    let overview: String?
    let genreIds: [Int]

    var id: Int { tmdbId }

    enum CodingKeys: String, CodingKey {
        case tmdbId = "tmdb_id"
        case title
        case year
        case posterPath = "poster_path"
        case overview
        case genreIds = "genre_ids"
    }
}
