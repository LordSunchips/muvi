import Foundation

struct SettingsDTO: Codable {
    let displayMetric: DisplayMetric
    enum CodingKeys: String, CodingKey { case displayMetric = "display_metric" }
}

private struct UpdateSettingsBody: Encodable {
    let displayMetric: DisplayMetric
    enum CodingKeys: String, CodingKey { case displayMetric = "display_metric" }
}

struct SettingsAPI {
    let client: APIClient

    func get() async throws -> SettingsDTO {
        try await client.get("/settings")
    }

    func update(displayMetric: DisplayMetric) async throws -> SettingsDTO {
        try await client.patch("/settings", body: UpdateSettingsBody(displayMetric: displayMetric))
    }
}
