import SwiftUI

/// Search TMDB and tap a result to add it to the library. `onAdd` returns after the network call
/// completes so this view can dismiss.
struct AddMovieView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var query = ""
    @State private var results: [TMDBSearchResultDTO] = []
    @State private var isSearching = false
    @State private var addingId: Int?
    @State private var lastError: String?

    private let tmdb = TMDBAPI(client: APIClient())
    private var searchDebounceTask: Task<Void, Never>? {
        get { nil } set { _ = newValue }
    }

    let onAdd: (Int) async -> LibraryMovieDTO?

    var body: some View {
        NavigationStack {
            List {
                if isSearching {
                    HStack {
                        ProgressView()
                        Text("Searching…").foregroundStyle(.secondary)
                    }
                }
                ForEach(results) { result in
                    Button {
                        Task { await addMovie(result) }
                    } label: {
                        AddMovieRow(result: result, isAdding: addingId == result.tmdbId)
                    }
                    .buttonStyle(.plain)
                    .disabled(addingId != nil)
                }
                if let lastError {
                    Text(lastError)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }
            }
            .listStyle(.plain)
            .searchable(text: $query, prompt: "Search TMDB")
            .onChange(of: query) { _, newValue in
                Task { await runSearch(for: newValue) }
            }
            .navigationTitle("Add a movie")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }

    private func runSearch(for text: String) async {
        // Debounce so we don't fire on every keystroke.
        try? await Task.sleep(nanoseconds: 300_000_000)
        if text != query { return }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            results = []
            return
        }
        isSearching = true
        defer { isSearching = false }
        do {
            results = try await tmdb.search(query: trimmed)
            lastError = nil
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func addMovie(_ result: TMDBSearchResultDTO) async {
        addingId = result.tmdbId
        defer { addingId = nil }
        if await onAdd(result.tmdbId) != nil {
            dismiss()
        } else {
            // Parent's LibraryStore set its own lastError; surface a light hint here too so the
            // user knows the tap didn't silently no-op.
            lastError = "Couldn't add — see the library screen for details."
        }
    }
}

struct AddMovieRow: View {
    let result: TMDBSearchResultDTO
    let isAdding: Bool

    var body: some View {
        HStack(spacing: 12) {
            PosterView(path: result.posterPath, width: 56)
            VStack(alignment: .leading, spacing: 4) {
                Text(result.title)
                    .font(.body.weight(.semibold))
                    .lineLimit(2)
                if let year = result.year {
                    Text(String(year))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if let overview = result.overview, !overview.isEmpty {
                    Text(overview)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
            }
            Spacer()
            if isAdding {
                ProgressView()
            } else {
                Image(systemName: "plus.circle.fill")
                    .foregroundStyle(.tint)
                    .font(.title3)
            }
        }
        .padding(.vertical, 4)
    }
}
