import SwiftUI

struct BucketPickerView: View {
    let movie: LibraryMovieDTO
    let onPick: (Bucket) -> Void

    var body: some View {
        VStack(spacing: 24) {
            VStack(spacing: 8) {
                PosterView(path: movie.posterPath, width: 120)
                Text(movie.title)
                    .font(.title3.weight(.semibold))
                    .multilineTextAlignment(.center)
                if let year = movie.year {
                    Text(String(year))
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.top, 8)

            Text("How did it feel?")
                .font(.headline)
                .padding(.top, 4)

            VStack(spacing: 12) {
                ForEach(Bucket.allCases) { bucket in
                    Button {
                        onPick(bucket)
                    } label: {
                        HStack {
                            Text(bucket.displayName)
                                .font(.title3.weight(.semibold))
                            Spacer()
                            Image(systemName: iconName(bucket))
                                .font(.title3)
                        }
                        .foregroundStyle(bucket.tint)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(bucket.tint.opacity(0.15), in: RoundedRectangle(cornerRadius: 14))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal)

            Spacer()
        }
    }

    private func iconName(_ bucket: Bucket) -> String {
        switch bucket {
        case .loved: return "heart.fill"
        case .fine: return "hand.thumbsup"
        case .bad: return "hand.thumbsdown"
        }
    }
}
