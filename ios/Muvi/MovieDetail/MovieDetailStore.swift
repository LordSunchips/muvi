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

    func deleteRanking(_ ranking: RankingDTO) async {
        do {
            try await api.deleteRanking(rankingId: ranking.id)
            await refresh()
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    /// Edit a ranking's captured note and/or watch date. `clearWatchedOn == true` sends null so
    /// the server drops the date; `false` with `watchedOn == nil` leaves the field unchanged.
    func updateRanking(
        _ ranking: RankingDTO,
        note: String?,
        watchedOn: Date?,
        clearWatchedOn: Bool
    ) async -> Bool {
        do {
            _ = try await api.updateRanking(
                rankingId: ranking.id,
                note: note,
                watchedOn: watchedOn,
                clearWatchedOn: clearWatchedOn
            )
            await refresh()
            return true
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
            return false
        }
    }

    func clearError() { lastError = nil }
}
