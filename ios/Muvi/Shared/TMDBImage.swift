import Foundation

enum TMDBImage {
    /// Resolve a TMDB relative poster path (e.g. "/poster.jpg") to a full URL at the given size.
    static func posterURL(path: String?, size: String = "w342") -> URL? {
        guard let path, !path.isEmpty else { return nil }
        return URL(string: "https://image.tmdb.org/t/p/\(size)\(path)")
    }
}
