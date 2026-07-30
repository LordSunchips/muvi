import SwiftUI

struct MovieDetailView: View {
    let movieId: Int
    let onLibraryChanged: () -> Void

    @State private var store: MovieDetailStore
    @State private var isPresentingRank = false
    @State private var isPresentingAddWatch = false

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
            .sheet(isPresented: $isPresentingRank) {
                if let detail = store.detail {
                    RankFlowView(movie: detail.asLibraryMovie) {
                        Task {
                            await store.refresh()
                            onLibraryChanged()
                        }
                    }
                }
            }
            .sheet(isPresented: $isPresentingAddWatch) {
                AddWatchView { date, note in
                    await store.addWatch(on: date, note: note)
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
                rankSection(detail)
                watchesSection(detail)
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

    private func rankSection(_ detail: MovieDetailDTO) -> some View {
        Section {
            Button {
                isPresentingRank = true
            } label: {
                Label(detail.rankings.isEmpty ? "Rank this movie" : "Rank again", systemImage: "arrow.up.arrow.down")
            }
            if detail.rankings.isEmpty {
                Text("No rankings yet.")
                    .foregroundStyle(.secondary)
                    .font(.footnote)
            } else {
                ForEach(detail.rankings) { ranking in
                    RankingHistoryRow(ranking: ranking)
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
            Text("Rank history")
        } footer: {
            Text("Latest ranking shown at the top. Swipe left to delete.")
        }
    }

    private func watchesSection(_ detail: MovieDetailDTO) -> some View {
        Section {
            Button {
                isPresentingAddWatch = true
            } label: {
                Label("Log a watch", systemImage: "eye")
            }
            if detail.watches.isEmpty {
                Text("No watches logged yet.")
                    .foregroundStyle(.secondary)
                    .font(.footnote)
            } else {
                ForEach(detail.watches) { watch in
                    WatchHistoryRow(watch: watch)
                        .swipeActions {
                            Button(role: .destructive) {
                                Task { await store.deleteWatch(watch) }
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                }
            }
        } header: {
            Text("Watch log")
        }
    }
}

private struct RankingHistoryRow: View {
    let ranking: RankingDTO

    var body: some View {
        HStack {
            BucketBadge(bucket: ranking.bucket)
            VStack(alignment: .leading, spacing: 2) {
                Text(ranking.createdAt.formatted(date: .abbreviated, time: .shortened))
                    .font(.subheadline)
                if let note = ranking.note, !note.isEmpty {
                    Text(note)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
            }
            Spacer()
            Text(String(format: "%.1f", ranking.score))
                .font(.body.weight(.semibold))
                .monospacedDigit()
                .foregroundStyle(ranking.bucket.tint)
        }
    }
}

private struct WatchHistoryRow: View {
    let watch: WatchDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(watch.watchedOn.formatted(date: .abbreviated, time: .omitted))
                .font(.subheadline.weight(.semibold))
            if let note = watch.note, !note.isEmpty {
                Text(note)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }
}
