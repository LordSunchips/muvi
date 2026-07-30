import Foundation

private struct AddMovieBody: Encodable {
    let tmdbId: Int
    enum CodingKeys: String, CodingKey { case tmdbId = "tmdb_id" }
}

struct LibraryAPI {
    let client: APIClient

    func list(genreId: Int? = nil, bucket: Bucket? = nil) async throws -> [LibraryMovieDTO] {
        var query: [URLQueryItem] = []
        if let genreId { query.append(URLQueryItem(name: "genre_id", value: String(genreId))) }
        if let bucket { query.append(URLQueryItem(name: "bucket", value: bucket.rawValue)) }
        return try await client.get("/library", query: query)
    }

    func add(tmdbId: Int) async throws -> LibraryMovieDTO {
        try await client.post("/library", body: AddMovieBody(tmdbId: tmdbId))
    }

    func remove(movieId: Int) async throws {
        try await client.delete("/library/\(movieId)")
    }
}
