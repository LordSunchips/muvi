import SwiftUI

/// Fixed-aspect (2:3) movie poster. Shows a placeholder chip while loading or if the URL is nil.
struct PosterView: View {
    let path: String?
    var width: CGFloat = 60

    var body: some View {
        let height = width * 1.5
        Group {
            if let url = TMDBImage.posterURL(path: path) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .empty:
                        placeholder
                    case .success(let image):
                        image.resizable().scaledToFill()
                    case .failure:
                        placeholder
                    @unknown default:
                        placeholder
                    }
                }
            } else {
                placeholder
            }
        }
        .frame(width: width, height: height)
        .clipShape(RoundedRectangle(cornerRadius: 6))
        .background(RoundedRectangle(cornerRadius: 6).fill(Color(.tertiarySystemFill)))
    }

    private var placeholder: some View {
        Image(systemName: "film")
            .foregroundStyle(.secondary)
    }
}
