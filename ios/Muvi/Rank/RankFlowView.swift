import SwiftUI

/// Sheet that walks the user through the Beli rank flow for `movie`. Two modes:
/// - ``RankStore/Mode/logWatch``: date + note step first, then bucket + comparisons.
/// - ``RankStore/Mode/rerank``: straight to bucket + comparisons; the resulting ranking has no
///   watched_on date.
struct RankFlowView: View {
    let movie: LibraryMovieDTO
    let mode: RankStore.Mode
    let onFinished: () -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var store: RankStore

    init(movie: LibraryMovieDTO, mode: RankStore.Mode, onFinished: @escaping () -> Void) {
        self.movie = movie
        self.mode = mode
        self.onFinished = onFinished
        _store = State(initialValue: RankStore(movie: movie, mode: mode))
    }

    var body: some View {
        NavigationStack {
            content
                .navigationTitle(mode == .logWatch ? "Log a watch" : "Re-rank")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Close") { dismiss() }
                    }
                }
                .alert(
                    "Something went wrong",
                    isPresented: Binding(get: { store.lastError != nil }, set: { _ in })
                ) {
                    Button("OK", role: .cancel) {}
                } message: {
                    Text(store.lastError ?? "")
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch store.step {
        case .pickingDateNote:
            WatchDetailsView(
                movie: movie,
                watchedOn: Binding(get: { store.pendingWatchedOn }, set: { store.pendingWatchedOn = $0 }),
                note: Binding(get: { store.pendingNote }, set: { store.pendingNote = $0 })
            ) {
                store.confirmDateNote()
            }
        case .pickingBucket:
            BucketPickerView(movie: movie) { bucket in
                Task { await store.start(bucket: bucket) }
            }
        case .starting:
            loading("Finding the first opponent…")
        case .comparing(_, let opponent):
            ComparisonView(subject: movie, opponent: opponent, isSubmitting: false) { winnerId in
                Task { await store.pickWinner(winnerId) }
            }
        case .submittingCompare:
            if let opponent = store.currentOpponent {
                ComparisonView(subject: movie, opponent: opponent, isSubmitting: true) { _ in }
            } else {
                loading("Placing…")
            }
        case .finished(let ranking):
            RankResultView(movie: movie, ranking: ranking) {
                onFinished()
                dismiss()
            }
        }
    }

    private func loading(_ label: String) -> some View {
        VStack(spacing: 12) {
            ProgressView()
            Text(label).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
