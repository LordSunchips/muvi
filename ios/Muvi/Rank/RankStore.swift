import Foundation
import Observation

/// Drives the multi-step Beli ranking flow for a single movie.
///
/// The state machine is: ``pickingBucket`` → (server may finalize immediately if the bucket is
/// empty, jumping to ``finished``) → ``comparing`` → repeat compare with new opponents →
/// ``finished``. Errors surface via ``lastError`` and don't advance the state.
@MainActor
@Observable
final class RankStore {
    enum Step: Equatable {
        case pickingBucket
        case starting
        case comparing(sessionId: Int, opponent: OpponentDTO)
        case submittingCompare
        case finished(RankingDTO)
    }

    let movie: LibraryMovieDTO
    private(set) var step: Step = .pickingBucket
    private(set) var lastError: String?

    private let api: RankAPI

    init(movie: LibraryMovieDTO, api: RankAPI = RankAPI(client: APIClient())) {
        self.movie = movie
        self.api = api
    }

    var currentOpponent: OpponentDTO? {
        if case .comparing(_, let opponent) = step { return opponent }
        return nil
    }

    var currentSessionId: Int? {
        if case .comparing(let id, _) = step { return id }
        return nil
    }

    var isBusy: Bool {
        switch step {
        case .starting, .submittingCompare: return true
        default: return false
        }
    }

    func start(bucket: Bucket) async {
        step = .starting
        lastError = nil
        do {
            let result = try await api.start(movieId: movie.id, bucket: bucket, note: nil)
            apply(result)
        } catch {
            step = .pickingBucket
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    func pickWinner(_ winnerMovieId: Int) async {
        guard case .comparing(let sessionId, let opponent) = step else { return }
        step = .submittingCompare
        lastError = nil
        do {
            let result = try await api.compare(sessionId: sessionId, winnerMovieId: winnerMovieId)
            apply(result)
        } catch {
            step = .comparing(sessionId: sessionId, opponent: opponent)
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func apply(_ result: RankStepDTO) {
        if result.done, let ranking = result.ranking {
            step = .finished(ranking)
        } else if let sessionId = result.sessionId, let opponent = result.opponent {
            step = .comparing(sessionId: sessionId, opponent: opponent)
        } else {
            step = .pickingBucket
            lastError = "The server returned an unexpected ranking response."
        }
    }
}
