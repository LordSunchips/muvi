import SwiftUI

struct LibraryView: View {
    @Environment(AuthStore.self) private var auth
    @State private var library = LibraryStore()
    @State private var isPresentingAdd = false

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
                        Menu {
                            Button("Log out", role: .destructive) { auth.logout() }
                        } label: {
                            Image(systemName: "person.crop.circle")
                        }
                    }
                }
                .refreshable { await library.refresh() }
                .task { await library.refresh() }
                .sheet(isPresented: $isPresentingAdd) {
                    AddMovieView { tmdbId in
                        await library.add(tmdbId: tmdbId)
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
                LibraryRow(movie: movie)
            }
            .listStyle(.plain)
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

