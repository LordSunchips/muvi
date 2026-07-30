import Foundation
import Observation

@MainActor
@Observable
final class SettingsStore {
    private(set) var displayMetric: DisplayMetric = .latest
    private(set) var isLoading = false
    private(set) var lastError: String?

    private let api: SettingsAPI

    init(api: SettingsAPI = SettingsAPI(client: APIClient())) {
        self.api = api
    }

    func refresh() async {
        isLoading = true
        defer { isLoading = false }
        do {
            displayMetric = try await api.get().displayMetric
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }

    func update(_ metric: DisplayMetric) async {
        do {
            let updated = try await api.update(displayMetric: metric)
            displayMetric = updated.displayMetric
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
