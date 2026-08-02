import SwiftUI

struct RankResultView: View {
    let movie: LibraryMovieDTO
    let ranking: RankingDTO
    let onDone: () -> Void

    @State private var showScore = false

    var body: some View {
        VStack(spacing: 20) {
            PosterView(path: movie.posterPath, width: 140)
            Text(movie.title)
                .font(.title3.weight(.semibold))
                .multilineTextAlignment(.center)

            BucketBadge(bucket: ranking.bucket)

            Text(String(format: "%.1f", ranking.score))
                .font(.system(size: 72, weight: .bold, design: .rounded))
                .monospacedDigit()
                .foregroundStyle(ranking.bucket.tint)
                .scaleEffect(showScore ? 1.0 : 0.4)
                .opacity(showScore ? 1.0 : 0.0)
                .animation(.spring(response: 0.55, dampingFraction: 0.6), value: showScore)

            Text("out of 10")
                .font(.footnote)
                .foregroundStyle(.secondary)

            Spacer()

            Button {
                onDone()
            } label: {
                Text("Done").fontWeight(.semibold)
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.accentColor)
            .foregroundStyle(.white)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .padding(.horizontal)
            .padding(.bottom)
        }
        .padding(.top, 32)
        .onAppear { showScore = true }
    }
}
