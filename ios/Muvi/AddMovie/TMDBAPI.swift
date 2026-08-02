import Foundation

struct TMDBAPI {
    let client: APIClient

    func search(query: String) async throws -> [TMDBSearchResultDTO] {
        let items = [URLQueryItem(name: "q", value: query)]
        return try await client.get("/tmdb/search", query: items)
    }

    func genres() async throws -> [GenreDTO] {
        try await client.get("/tmdb/genres")
    }
}
