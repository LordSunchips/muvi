import Foundation

enum AppConfig {
    /// Base URL for the muvi backend. Resolution order:
    /// 1. `MUVI_API_BASE_URL` set on the current process (e.g. via Xcode scheme env vars).
    /// 2. `MUVI_API_BASE_URL` string in Info.plist (baked in per configuration if you want).
    /// 3. The compiled-in default below (change to your prod URL for release builds).
    static let apiBaseURL: URL = {
        if let env = ProcessInfo.processInfo.environment["MUVI_API_BASE_URL"],
           let url = URL(string: env) { return url }
        if let plist = Bundle.main.object(forInfoDictionaryKey: "MUVI_API_BASE_URL") as? String,
           let url = URL(string: plist) { return url }
        return URL(string: defaultBaseURL)!
    }()

    /// Change this to your Fly.io URL (or wherever the backend lives) before shipping to a device.
    /// Keep `http://127.0.0.1:8000` for simulator-vs-Mac dev.
    #if DEBUG
    private static let defaultBaseURL = "http://127.0.0.1:8000"
    #else
    private static let defaultBaseURL = "https://muvi-backend.fly.dev"
    #endif
}
