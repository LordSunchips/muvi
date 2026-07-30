import Foundation

struct RankAPI {
    let client: APIClient

    func start(movieId: Int, bucket: Bucket, note: String?) async throws -> RankStepDTO {
        try await client.post("/rank/start", body: RankStartRequest(movieId: movieId, bucket: bucket, note: note))
    }

    func compare(sessionId: Int, winnerMovieId: Int) async throws -> RankStepDTO {
        try await client.post("/rank/\(sessionId)/compare", body: RankCompareRequest(winnerMovieId: winnerMovieId))
    }
}
