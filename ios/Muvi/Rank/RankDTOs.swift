import Foundation

struct OpponentDTO: Codable, Hashable, Identifiable {
    let movieId: Int
    let title: String
    let year: Int?
    let posterPath: String?

    var id: Int { movieId }

    enum CodingKeys: String, CodingKey {
        case movieId = "movie_id"
        case title
        case year
        case posterPath = "poster_path"
    }
}

struct RankingDTO: Codable, Hashable, Identifiable {
    let id: Int
    let movieId: Int
    let bucket: Bucket
    let score: Double
    let note: String?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case movieId = "movie_id"
        case bucket
        case score
        case note
        case createdAt = "created_at"
    }
}

struct RankStepDTO: Decodable {
    let done: Bool
    let sessionId: Int?
    let opponent: OpponentDTO?
    let ranking: RankingDTO?

    enum CodingKeys: String, CodingKey {
        case done
        case sessionId = "session_id"
        case opponent
        case ranking
    }
}

struct RankStartRequest: Encodable {
    let movieId: Int
    let bucket: Bucket
    let note: String?

    enum CodingKeys: String, CodingKey {
        case movieId = "movie_id"
        case bucket
        case note
    }
}

struct RankCompareRequest: Encodable {
    let winnerMovieId: Int
    enum CodingKeys: String, CodingKey { case winnerMovieId = "winner_movie_id" }
}
