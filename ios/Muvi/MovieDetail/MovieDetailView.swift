import SwiftUI

struct MovieDetailView: View {
    let movieId: Int
    let onLibraryChanged: () -> Void

    @State private var store: MovieDetailStore
    /// Simultaneous state: which rank flow (if any) is presented, and — when a per-genre re-rank
    /// is chosen — which genre it's scoped to. Wrapped so `.sheet(item:)` can drive it.
    @State private var rankPresentation: RankPresentation?
    /// Ranking currently being edited via the EditRankingView sheet.
    @State private var editingRanking: RankingDTO?

    struct RankPresentation: Identifiable {
        let mode: RankStore.Mode
        let genre: GenreDTO?
        var id: String { "\(mode.rawValue)-\(genre?.id ?? -1)" }
    }

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
            .sheet(item: $rankPresentation) { presentation in
                if let detail = store.detail {
                    RankFlowView(
                        movie: detail.asLibraryMovie,
                        mode: presentation.mode,
                        genre: presentation.genre
                    ) {
                        Task {
                            await store.refresh()
                            onLibraryChanged()
                        }
                    }
                }
            }
            .sheet(item: $editingRanking) { ranking in
                EditRankingView(ranking: ranking) { note, watchedOn, clearWatchedOn in
                    let ok = await store.updateRanking(
                        ranking,
                        note: note,
                        watchedOn: watchedOn,
                        clearWatchedOn: clearWatchedOn
                    )
                    if ok { onLibraryChanged() }
                    return ok
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
                rankPresentation = RankPresentation(mode: .logWatch, genre: nil)
            } label: {
                Label("Log a watch", systemImage: "eye")
                    .fontWeight(.semibold)
            }
            if !detail.rankings.isEmpty {
                Button {
                    rankPresentation = RankPresentation(mode: .rerank, genre: nil)
                } label: {
                    Label("Re-rank without logging watch", systemImage: "arrow.up.arrow.down")
                        .foregroundStyle(.secondary)
                }
            }
            if !detail.genres.isEmpty {
                Menu {
                    ForEach(detail.genres) { genre in
                        Button("Re-rank in \(genre.name)") {
                            rankPresentation = RankPresentation(mode: .rerank, genre: genre)
                        }
                    }
                } label: {
                    Label("Re-rank within a genre", systemImage: "square.stack.3d.up")
                        .foregroundStyle(.secondary)
                }
            }
        } footer: {
            Text(detail.rankings.isEmpty
                 ? "Log a watch to add this movie to your ranked list."
                 : "Log a watch to record a viewing. Re-rank to adjust its global position, or re-rank inside a genre to give it a different score in that genre's filter.")
        }
    }

    private func historySection(_ detail: MovieDetailDTO) -> some View {
        let genreLookup = Dictionary(uniqueKeysWithValues: detail.genres.map { ($0.id, $0.name) })
        return Section {
            if detail.rankings.isEmpty {
                Text("Nothing logged yet.")
                    .foregroundStyle(.secondary)
                    .font(.footnote)
            } else {
                ForEach(detail.rankings) { ranking in
                    Button {
                        editingRanking = ranking
                    } label: {
                        HistoryRow(ranking: ranking, genreLookup: genreLookup)
                    }
                    .buttonStyle(.plain)
                    .swipeActions {
                        Button(role: .destructive) {
                            Task { await store.deleteRanking(ranking) }
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                        Button {
                            editingRanking = ranking
                        } label: {
                            Label("Edit", systemImage: "pencil")
                        }
                        .tint(.accentColor)
                    }
                }
            }
        } header: {
            Text("History")
        } footer: {
            Text("Rows with a date are watches. Rows without are re-ranks. Tap a row to edit its date and notes, swipe left to delete.")
        }
    }
}

private struct HistoryRow: View {
    let ranking: RankingDTO
    let genreLookup: [Int: String]

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
                if let genreId = ranking.genreId, let name = genreLookup[genreId] {
                    Text("in \(name)")
                        .font(.caption2.weight(.semibold))
                        .textCase(.uppercase)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.accentColor.opacity(0.15), in: Capsule())
                        .foregroundStyle(Color.accentColor)
                }
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
