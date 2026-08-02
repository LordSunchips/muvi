import Foundation
import Observation

/// Owns the user's library list. `refresh()` re-fetches; `add(tmdbId:)` calls the backend and
/// prepends the new movie so the UI updates without a full round-trip. Errors surface via
/// `lastError`; the caller decides whether to present them.
@MainActor
@Observable
final class LibraryStore {
    private(set) var movies: [LibraryMovieDTO] = []
    private(set) var isLoading = false
    private(set) var lastError: String?
    private(set) var genreFilter: GenreDTO?
    private(set) var bucketFilter: Bucket?

    /// Genres derived from the union of all library movies' genres. Used to populate the filter
    /// menu without needing a separate /tmdb/genres call.
    private(set) var availableGenres: [GenreDTO] = []
    /// Cached full library (unfiltered by genre) so we can compute availableGenres and switch
    /// filters without a round-trip. `movies` above is the filtered view.
    private var allMovies: [LibraryMovieDTO] = []

    private let api: LibraryAPI

    init(api: LibraryAPI = LibraryAPI(client: APIClient())) {
        self.api = api
    }

    func setGenreFilter(_ genre: GenreDTO?) {
        genreFilter = genre
        Task { await refresh() }
    }

    func setBucketFilter(_ bucket: Bucket?) {
        bucketFilter = bucket
        Task { await refresh() }
    }

    func refresh() async {
        isLoading = true
        lastError = nil
        defer { isLoading = false }
        do {
            movies = try await api.list(genreId: genreFilter?.id, bucket: bucketFilter)
            // Refresh the genre menu from an unfiltered fetch, but only when we don't already
            // have a cache — most refreshes are same-filter and don't need a second call.
            if allMovies.isEmpty || genreFilter == nil {
                allMovies = try await api.list(genreId: nil, bucket: nil)
                availableGenres = allMovies
                    .flatMap(\.genres)
                    .reduce(into: [Int: GenreDTO]()) { acc, g in acc[g.id] = g }
                    .values
                    .sorted { $0.name < $1.name }
            }
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    @discardableResult
    func add(tmdbId: Int) async -> LibraryMovieDTO? {
        do {
            let movie = try await api.add(tmdbId: tmdbId)
            movies.insert(movie, at: 0)
            allMovies.insert(movie, at: 0)
            for genre in movie.genres where !availableGenres.contains(where: { $0.id == genre.id }) {
                availableGenres.append(genre)
                availableGenres.sort { $0.name < $1.name }
            }
            return movie
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
            return nil
        }
    }

    func clearError() {
        lastError = nil
    }

    func remove(_ movie: LibraryMovieDTO) async {
        do {
            try await api.remove(movieId: movie.id)
            movies.removeAll { $0.id == movie.id }
            allMovies.removeAll { $0.id == movie.id }
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
