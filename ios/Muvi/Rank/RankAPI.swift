import Foundation

struct RankAPI {
    let client: APIClient

    private static let dayFormatter: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(identifier: "UTC")
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()

    func start(movieId: Int, bucket: Bucket, note: String?, watchedOn: Date?) async throws -> RankStepDTO {
        let dateString = watchedOn.map { Self.dayFormatter.string(from: $0) }
        let body = RankStartRequest(movieId: movieId, bucket: bucket, note: note, watchedOn: dateString)
        return try await client.post("/rank/start", body: body)
    }

    func compare(sessionId: Int, winnerMovieId: Int) async throws -> RankStepDTO {
        try await client.post("/rank/\(sessionId)/compare", body: RankCompareRequest(winnerMovieId: winnerMovieId))
    }
}
