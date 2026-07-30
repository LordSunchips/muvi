import SwiftUI

struct MovieDetailView: View {
    let movieId: Int
    let onLibraryChanged: () -> Void

    @State private var store: MovieDetailStore
    @State private var rankMode: RankStore.Mode?

    init(movieId: Int, onLibraryChanged: @escaping () -> Void) {
        self.movieId = movieId
        self.onLibraryChanged = onLibraryChanged
        _store = State(initialValue: MovieDetailStore(movieId: movieId))
    }

    var body: some View {
        content
            .task { await store.refresh() }
            .refreshable { await store.refresh() }
            .navigationTitle(store.detail?.title ?? "Loading…")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(item: $rankMode) { mode in
                if let detail = store.detail {
                    RankFlowView(movie: detail.asLibraryMovie, mode: mode) {
                        Task {
                            await store.refresh()
                            onLibraryChanged()
                        }
                    }
                }
            }
            .alert(
                "Something went wrong",
                isPresented: Binding(
                    get: { store.lastError != nil },
                    set: { if !$0 { store.clearError() } }
                )
            ) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(store.lastError ?? "")
            }
    }

    @ViewBuilder
    private var content: some View {
        if let detail = store.detail {
            List {
                header(detail)
                actions(detail)
                historySection(detail)
            }
            .listStyle(.insetGrouped)
        } else if store.isLoading {
            ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
        } else {
            Text("No detail available.")
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private func header(_ detail: MovieDetailDTO) -> some View {
        Section {
            HStack(alignment: .top, spacing: 14) {
                PosterView(path: detail.posterPath, width: 100)
                VStack(alignment: .leading, spacing: 6) {
                    Text(detail.title)
                        .font(.title3.weight(.semibold))
                    if let year = detail.year {
                        Text(String(year))
                            .foregroundStyle(.secondary)
                    }
                    HStack(spacing: 8) {
                        if let bucket = detail.bucket {
                            BucketBadge(bucket: bucket)
                        }
                        if let score = detail.score {
                            Text(String(format: "%.1f", score))
                                .font(.title2.weight(.bold))
                                .monospacedDigit()
                        }
                    }
                    if !detail.genres.isEmpty {
                        Text(detail.genres.map(\.name).joined(separator: " · "))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
            }
            .padding(.vertical, 6)
        }
    }

    private func actions(_ detail: MovieDetailDTO) -> some View {
        Section {
            Button {
                rankMode = .logWatch
            } label: {
                Label("Log a watch", systemImage: "eye")
                    .fontWeight(.semibold)
            }
            if !detail.rankings.isEmpty {
                Button {
                    rankMode = .rerank
                } label: {
                    Label("Re-rank without logging watch", systemImage: "arrow.up.arrow.down")
                        .foregroundStyle(.secondary)
                }
            }
        } footer: {
            Text(detail.rankings.isEmpty
                 ? "Log a watch to add this movie to your ranked list."
                 : "Log a watch to record a viewing. Re-rank to adjust its position without logging a viewing.")
        }
    }

    private func historySection(_ detail: MovieDetailDTO) -> some View {
        Section {
            if detail.rankings.isEmpty {
                Text("Nothing logged yet.")
                    .foregroundStyle(.secondary)
                    .font(.footnote)
            } else {
                ForEach(detail.rankings) { ranking in
                    HistoryRow(ranking: ranking)
                        .swipeActions {
                            Button(role: .destructive) {
                                Task { await store.deleteRanking(ranking) }
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                }
            }
        } header: {
            Text("History")
        } footer: {
            Text("Rows with a date are watches. Rows without are re-ranks. Swipe left to delete.")
        }
    }
}

private struct HistoryRow: View {
    let ranking: RankingDTO

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            BucketBadge(bucket: ranking.bucket)
            VStack(alignment: .leading, spacing: 3) {
                if let watchedOn = ranking.watchedOn {
                    Text("Watched \(watchedOn.formatted(date: .abbreviated, time: .omitted))")
                        .font(.subheadline.weight(.semibold))
                } else {
                    Text("Re-ranked")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
                Text(ranking.createdAt.formatted(date: .abbreviated, time: .shortened))
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                if let note = ranking.note, !note.isEmpty {
                    Text(note)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(3)
                        .padding(.top, 2)
                }
            }
            Spacer()
            Text(String(format: "%.1f", ranking.score))
                .font(.body.weight(.semibold))
                .monospacedDigit()
                .foregroundStyle(ranking.bucket.tint)
        }
        .padding(.vertical, 2)
    }
}
