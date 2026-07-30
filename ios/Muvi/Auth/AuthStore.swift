import Foundation
import Observation

/// Global auth state: current user + convenience helpers to sign in / sign up / log out.
///
/// Persistence lives in the Keychain — the token is restored on init. `isAuthenticated` is
/// a stored (observable) property, not a computed one, because SwiftUI can only react to
/// property changes on this object; the Keychain itself isn't observable.
@MainActor
@Observable
final class AuthStore {
    private(set) var currentUser: UserDTO?
    private(set) var isAuthenticated: Bool
    private(set) var isAuthenticating = false
    private(set) var lastError: String?

    private let api: AuthAPI
    private let tokenStore: KeychainStore

    init(api: AuthAPI = AuthAPI(client: APIClient()), tokenStore: KeychainStore = .shared) {
        self.api = api
        self.tokenStore = tokenStore
        self.isAuthenticated = tokenStore.token != nil
    }

    func signup(email: String, password: String) async {
        await perform { try await self.api.signup(email: email, password: password) }
    }

    func login(email: String, password: String) async {
        await perform { try await self.api.login(email: email, password: password) }
    }

    func logout() {
        tokenStore.token = nil
        currentUser = nil
        isAuthenticated = false
    }

    private func perform(_ call: () async throws -> AuthTokenResponse) async {
        isAuthenticating = true
        lastError = nil
        defer { isAuthenticating = false }
        do {
            let result = try await call()
            tokenStore.token = result.accessToken
            currentUser = result.user
            isAuthenticated = true
        } catch let error as APIError {
            lastError = error.errorDescription
        } catch {
            lastError = error.localizedDescription
        }
    }
}
