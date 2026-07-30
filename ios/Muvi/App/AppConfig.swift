import Foundation

enum AppConfig {
    /// The muvi backend base URL. Simulator can reach the host Mac's localhost via 127.0.0.1.
    static let apiBaseURL = URL(string: "http://127.0.0.1:8000")!
}
