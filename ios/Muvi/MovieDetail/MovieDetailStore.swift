import Foundation
import Observation

@MainActor
@Observable
final class MovieDetailStore {
    let movieId: Int
    private(set) var detail: MovieDetailDTO?
    private(set) var isLoading = false
    private(set) var lastError: String?

    private let api: MovieDetailAPI

    init(movieId: Int, api: MovieDetailAPI = MovieDetailAPI(client: APIClient())) {
        self.movieId = movieId
        self.api = api
    }

    func refresh() async {
        isLoading = true
        lastError = nil
        defer { isLoading = false }
        do {
            detail = try await api.detail(movieId: movieId)
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    func addWatch(on date: Date, note: String?) async {
        do {
            _ = try await api.addWatch(movieId: movieId, watchedOn: date, note: note)
            await refresh()
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    func deleteWatch(_ watch: WatchDTO) async {
        do {
            try await api.deleteWatch(watchId: watch.id)
            await refresh()
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    func deleteRanking(_ ranking: RankingDTO) async {
        do {
            try await api.deleteRanking(rankingId: ranking.id)
            await refresh()
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    func clearError() { lastError = nil }
}
