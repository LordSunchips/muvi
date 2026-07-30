import SwiftUI

/// Temporary landing screen so task 6 has an authenticated shell to look at.
/// The real library / rank / detail views land in tasks 7–10 and replace this.
struct LoggedInPlaceholderView: View {
    @Environment(AuthStore.self) private var auth

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Image(systemName: "film.stack")
                    .font(.system(size: 60))
                    .foregroundStyle(.tint)
                Text("Signed in")
                    .font(.title2.bold())
                if let user = auth.currentUser {
                    Text(user.email)
                        .foregroundStyle(.secondary)
                }
                Text("Library, ranking, and movie detail land in the next tasks.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .navigationTitle("muvi")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Log out") { auth.logout() }
                }
            }
        }
    }
}
