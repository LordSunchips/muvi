import Foundation

struct MovieDetailAPI {
    let client: APIClient

    func detail(movieId: Int) async throws -> MovieDetailDTO {
        try await client.get("/movies/\(movieId)")
    }

    func deleteRanking(rankingId: Int) async throws {
        try await client.delete("/rankings/\(rankingId)")
    }
}
