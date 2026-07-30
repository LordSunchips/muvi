import SwiftUI

struct LibraryView: View {
    @Environment(AuthStore.self) private var auth
    @State private var library = LibraryStore()
    @State private var isPresentingAdd = false
    @State private var isPresentingSettings = false
    // Set when AddMovieView returns a newly-added movie; consumed by the sheet's onDismiss
    // handler to open the log-a-watch flow so add-then-rank is a single continuous action.
    @State private var justAddedMovie: LibraryMovieDTO?
    @State private var pendingLogWatchMovie: LibraryMovieDTO?

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Library")
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button {
                            isPresentingAdd = true
                        } label: {
                            Image(systemName: "plus")
                        }
                        .accessibilityLabel("Add movie")
                    }
                    ToolbarItem(placement: .topBarLeading) {
                        Button {
                            isPresentingSettings = true
                        } label: {
                            Image(systemName: "person.crop.circle")
                        }
                        .accessibilityLabel("Settings")
                    }
                }
                .refreshable { await library.refresh() }
                .task { await library.refresh() }
                .sheet(isPresented: $isPresentingAdd, onDismiss: {
                    if let movie = justAddedMovie {
                        pendingLogWatchMovie = movie
                        justAddedMovie = nil
                    }
                }) {
                    AddMovieView { tmdbId in
                        let movie = await library.add(tmdbId: tmdbId)
                        justAddedMovie = movie
                        return movie
                    }
                }
                .sheet(item: $pendingLogWatchMovie) { movie in
                    RankFlowView(movie: movie, mode: .logWatch) {
                        Task { await library.refresh() }
                    }
                }
                .sheet(isPresented: $isPresentingSettings) {
                    SettingsView {
                        Task { await library.refresh() }
                    }
                }
                .alert(
                    "Something went wrong",
                    isPresented: Binding(get: { library.lastError != nil }, set: { if !$0 { library.clearError() } })
                ) {
                    Button("OK", role: .cancel) {}
                } message: {
                    Text(library.lastError ?? "")
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        if library.isLoading && library.movies.isEmpty {
            ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if library.movies.isEmpty {
            emptyState
        } else {
            List(library.movies) { movie in
                NavigationLink(value: movie.id) {
                    LibraryRow(movie: movie)
                }
                .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                    Button(role: .destructive) {
                        Task { await library.remove(movie) }
                    } label: {
                        Label("Remove", systemImage: "trash")
                    }
                }
            }
            .listStyle(.plain)
            .navigationDestination(for: Int.self) { movieId in
                MovieDetailView(movieId: movieId) {
                    Task { await library.refresh() }
                }
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "film.stack")
                .font(.system(size: 44))
                .foregroundStyle(.secondary)
            Text("No movies yet")
                .font(.headline)
            Text("Tap + to search TMDB and add your first film.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
