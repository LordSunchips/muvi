import SwiftUI

/// Two-poster comparison: user taps whichever movie was better; the tapped movie's id is reported
/// back so the RankStore can advance the binary search.
struct ComparisonView: View {
    let subject: LibraryMovieDTO
    let opponent: OpponentDTO
    let isSubmitting: Bool
    let onPick: (Int) -> Void

    var body: some View {
        VStack(spacing: 24) {
            Text("Which was better?")
                .font(.title3.weight(.semibold))
                .padding(.top, 8)

            HStack(spacing: 12) {
                candidateCard(title: subject.title, year: subject.year, posterPath: subject.posterPath) {
                    onPick(subject.id)
                }
                Text("or")
                    .font(.headline)
                    .foregroundStyle(.secondary)
                candidateCard(title: opponent.title, year: opponent.year, posterPath: opponent.posterPath) {
                    onPick(opponent.movieId)
                }
            }
            .padding(.horizontal, 12)
            .disabled(isSubmitting)

            if isSubmitting {
                ProgressView()
            }

            Spacer()

            // Describes the effect, not the mechanism: "binary search" and "bucket" are both
            // internal vocabulary, and "bucket" in particular is a word the user never sees —
            // they picked "Loved", "Fine" or "Bad".
            Text("Each answer narrows it down until \(subject.title) lands in the right spot.")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
                .padding(.bottom)
        }
    }

    @ViewBuilder
    private func candidateCard(title: String, year: Int?, posterPath: String?, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 8) {
                PosterView(path: posterPath, width: 140)
                Text(title)
                    .font(.subheadline.weight(.semibold))
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
                if let year { Text(String(year)).font(.caption).foregroundStyle(.secondary) }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 14))
        }
        .buttonStyle(.plain)
    }
}
