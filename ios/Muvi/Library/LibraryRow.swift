import SwiftUI

struct LibraryRow: View {
    let movie: LibraryMovieDTO

    var body: some View {
        HStack(spacing: 12) {
            PosterView(path: movie.posterPath, width: 56)
            VStack(alignment: .leading, spacing: 4) {
                Text(movie.title)
                    .font(.body.weight(.semibold))
                    .lineLimit(2)
                if let year = movie.year {
                    Text(String(year))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if let bucket = movie.bucket {
                    BucketBadge(bucket: bucket)
                        .padding(.top, 2)
                }
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                if let score = movie.score {
                    Text(String(format: "%.1f", score))
                        .font(.title3.weight(.bold))
                        .monospacedDigit()
                } else {
                    Text("—")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
                if movie.rankingCount > 1 {
                    Text("\(movie.rankingCount) ranks")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 4)
    }
}
