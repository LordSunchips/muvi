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

    var genreFilter: Int? { didSet { Task { await refresh() } } }
    var bucketFilter: Bucket? { didSet { Task { await refresh() } } }

    private let api: LibraryAPI

    init(api: LibraryAPI = LibraryAPI(client: APIClient())) {
        self.api = api
    }

    func refresh() async {
        isLoading = true
        lastError = nil
        defer { isLoading = false }
        do {
            movies = try await api.list(genreId: genreFilter, bucket: bucketFilter)
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    @discardableResult
    func add(tmdbId: Int) async -> LibraryMovieDTO? {
        do {
            let movie = try await api.add(tmdbId: tmdbId)
            movies.insert(movie, at: 0)
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
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
