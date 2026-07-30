import Foundation
import Observation

/// Drives the Beli rank flow for a single movie. Two entry-point modes:
///
/// - ``Mode/logWatch``: primary flow. Starts on the date/note step so the user records that they
///   watched the movie, then continues into the bucket picker + comparisons.
/// - ``Mode/rerank``: adjust an existing ranking. Skips the date/note step and lands directly on
///   the bucket picker; the resulting ranking has ``watched_on`` == nil.
@MainActor
@Observable
final class RankStore {
    enum Mode: String, Identifiable {
        case logWatch, rerank
        var id: String { rawValue }
    }

    enum Step: Equatable {
        case pickingDateNote
        case pickingBucket
        case starting
        case comparing(sessionId: Int, opponent: OpponentDTO)
        case submittingCompare
        case finished(RankingDTO)
    }

    let movie: LibraryMovieDTO
    let mode: Mode
    private(set) var step: Step
    private(set) var lastError: String?

    // Captured on the date/note screen; carried through to the API call.
    var pendingWatchedOn: Date = .now
    var pendingNote: String = ""

    private let api: RankAPI

    init(movie: LibraryMovieDTO, mode: Mode, api: RankAPI = RankAPI(client: APIClient())) {
        self.movie = movie
        self.mode = mode
        self.api = api
        self.step = (mode == .logWatch) ? .pickingDateNote : .pickingBucket
    }

    var currentOpponent: OpponentDTO? {
        if case .comparing(_, let opponent) = step { return opponent }
        return nil
    }

    var isBusy: Bool {
        switch step {
        case .starting, .submittingCompare: return true
        default: return false
        }
    }

    /// Advances past the date/note step. No-op in rerank mode.
    func confirmDateNote() {
        guard case .pickingDateNote = step else { return }
        step = .pickingBucket
    }

    func start(bucket: Bucket) async {
        step = .starting
        lastError = nil
        let trimmedNote = pendingNote.trimmingCharacters(in: .whitespacesAndNewlines)
        let note = (mode == .logWatch && !trimmedNote.isEmpty) ? trimmedNote : nil
        let watchedOn = (mode == .logWatch) ? pendingWatchedOn : nil
        do {
            let result = try await api.start(movieId: movie.id, bucket: bucket, note: note, watchedOn: watchedOn)
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
