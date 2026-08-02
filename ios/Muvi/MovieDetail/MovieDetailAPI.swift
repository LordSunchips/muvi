import Foundation

struct MovieDetailAPI {
    let client: APIClient

    private static let dayFormatter: DateFormatter = {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(identifier: "UTC")
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()

    func detail(movieId: Int) async throws -> MovieDetailDTO {
        try await client.get("/movies/\(movieId)")
    }

    func updateRanking(
        rankingId: Int,
        note: String?,
        watchedOn: Date?,
        clearWatchedOn: Bool
    ) async throws -> RankingDTO {
        // Build the JSON body by hand so we can distinguish "omit" (leave field unchanged) from
        // "send null" (clear the field). Encodable can't express that natively.
        var payload: [String: Any] = [:]
        if let note {
            payload["note"] = note
        } else {
            payload["note"] = NSNull()
        }
        if let watchedOn {
            payload["watched_on"] = Self.dayFormatter.string(from: watchedOn)
        } else if clearWatchedOn {
            payload["watched_on"] = NSNull()
        }
        let data = try JSONSerialization.data(withJSONObject: payload, options: [])
        return try await client.patchRaw("/rankings/\(rankingId)", body: data)
    }

    func deleteRanking(rankingId: Int) async throws {
        try await client.delete("/rankings/\(rankingId)")
    }
}
