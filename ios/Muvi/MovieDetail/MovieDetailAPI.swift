import Foundation

/// The backend expects `watched_on` as a plain ``yyyy-MM-dd`` string; encoding a Date directly
/// would serialize as ISO8601 with time. This encoder strips the time portion.
private let dayOnlyEncoder: JSONEncoder = {
    let e = JSONEncoder()
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = TimeZone(identifier: "UTC")
    formatter.dateFormat = "yyyy-MM-dd"
    e.dateEncodingStrategy = .formatted(formatter)
    return e
}()

struct MovieDetailAPI {
    let client: APIClient

    func detail(movieId: Int) async throws -> MovieDetailDTO {
        try await client.get("/movies/\(movieId)")
    }

    func addWatch(movieId: Int, watchedOn: Date, note: String?) async throws -> WatchDTO {
        // Bypass the shared encoder so watched_on serializes as a plain date.
        let body = try dayOnlyEncoder.encode(AddWatchBody(watchedOn: watchedOn, note: note))
        return try await client.postRaw("/movies/\(movieId)/watches", body: body)
    }

    func deleteWatch(watchId: Int) async throws {
        try await client.delete("/watches/\(watchId)")
    }

    func deleteRanking(rankingId: Int) async throws {
        try await client.delete("/rankings/\(rankingId)")
    }
}
