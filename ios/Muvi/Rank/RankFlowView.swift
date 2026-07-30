import SwiftUI

/// Sheet that walks the user through the whole Beli rank flow for `movie`. Calls `onFinished`
/// after the ranking lands so the presenter can refresh its library list.
struct RankFlowView: View {
    let movie: LibraryMovieDTO
    let onFinished: () -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var store: RankStore

    init(movie: LibraryMovieDTO, onFinished: @escaping () -> Void) {
        self.movie = movie
        self.onFinished = onFinished
        _store = State(initialValue: RankStore(movie: movie))
    }

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Rank")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Close") { dismiss() }
                    }
                }
                .alert(
                    "Something went wrong",
                    isPresented: Binding(
                        get: { store.lastError != nil },
                        set: { _ in }
                    )
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
