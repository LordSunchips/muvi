import Foundation

struct UserDTO: Codable, Identifiable, Hashable {
    let id: Int
    let email: String
}

struct AuthTokenResponse: Decodable {
    let accessToken: String
    let tokenType: String
    let user: UserDTO

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
        case user
    }
}

private struct CredentialsBody: Encodable {
    let email: String
    let password: String
}

struct AuthAPI {
    let client: APIClient

    func signup(email: String, password: String) async throws -> AuthTokenResponse {
        try await client.post("/auth/signup", body: CredentialsBody(email: email, password: password))
    }

    func login(email: String, password: String) async throws -> AuthTokenResponse {
        try await client.post("/auth/login", body: CredentialsBody(email: email, password: password))
    }

    /// Permanently deletes the signed-in account and all of its data. Irreversible.
    func deleteAccount() async throws {
        try await client.delete("/auth/me")
    }
}
