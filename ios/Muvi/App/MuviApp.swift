import SwiftUI

@main
struct MuviApp: App {
    @State private var auth = AuthStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(auth)
        }
    }
}

struct RootView: View {
    @Environment(AuthStore.self) private var auth

    var body: some View {
        Group {
            if auth.isAuthenticated {
                LibraryView()
            } else {
                AuthGateView()
            }
        }
    }
}
