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
        NotificationCenter.default.addObserver(
            forName: .muviSessionExpired,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in self?.handleSessionExpired() }
        }
    }

    private func handleSessionExpired() {
        // APIClient already cleared the token; mirror that in the observable state so the shell
        // routes us back to the auth gate. Avoid double-logging the reason as an alert; the caller
        // (e.g. LibraryStore) surfaces the underlying error separately.
        currentUser = nil
        isAuthenticated = false
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

    /// Permanently deletes the account server-side, then drops to the auth gate.
    ///
    /// Returns `true` on success. On failure the caller stays signed in and `lastError` explains
    /// why — logging out anyway would leave the user believing their data was erased when it
    /// wasn't, with no way back in to retry.
    @discardableResult
    func deleteAccount() async -> Bool {
        isAuthenticating = true
        lastError = nil
        defer { isAuthenticating = false }
        do {
            try await api.deleteAccount()
            logout()
            return true
        } catch let error as APIError {
            lastError = error.errorDescription
            return false
        } catch {
            lastError = error.localizedDescription
            return false
        }
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
