import SwiftUI

struct SettingsView: View {
    @Environment(AuthStore.self) private var auth
    @Environment(\.dismiss) private var dismiss
    @State private var settings = SettingsStore()
    @State private var isConfirmingDelete = false
    @State private var deletionError: String?
    let onSettingsChanged: () -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Picker("Display score as", selection: bindingForMetric()) {
                        ForEach(DisplayMetric.allCases) { metric in
                            Text(metric.displayName).tag(metric)
                        }
                    }
                } header: {
                    Text("Score metric")
                } footer: {
                    Text("How a movie's score is derived from its ranking history. 'Latest' uses the most recent rank; 'Mean' and 'Median' aggregate every rank you've given it.")
                }

                Section {
                    Button("Log out", role: .destructive) {
                        auth.logout()
                        dismiss()
                    }
                } header: {
                    if let email = auth.currentUser?.email {
                        Text(email)
                    }
                }

                // App Store Guideline 5.1.1(v): an app that lets you create an account has to let
                // you delete it from inside the app.
                Section {
                    Button("Delete account", role: .destructive) {
                        isConfirmingDelete = true
                    }
                    .disabled(auth.isAuthenticating)
                } footer: {
                    Text("Permanently deletes your account, your library, and every ranking you've logged. This can't be undone.")
                }

                Section {
                    Text("This product uses the TMDb API but is not endorsed or certified by TMDb.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
            .confirmationDialog(
                "Delete your account?",
                isPresented: $isConfirmingDelete,
                titleVisibility: .visible
            ) {
                Button("Delete account", role: .destructive) {
                    Task {
                        // On success `auth` flips to signed-out and the shell swaps in the auth
                        // gate; dismissing here just closes the sheet on top of it.
                        if await auth.deleteAccount() {
                            dismiss()
                        } else {
                            deletionError = auth.lastError ?? "Something went wrong. Please try again."
                        }
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Your library and ranking history will be erased. This can't be undone.")
            }
            .alert(
                "Couldn't delete account",
                isPresented: Binding(get: { deletionError != nil }, set: { if !$0 { deletionError = nil } })
            ) {
                Button("OK", role: .cancel) { deletionError = nil }
            } message: {
                Text(deletionError ?? "")
            }
            .task { await settings.refresh() }
        }
    }

    /// Two-way binding that persists the change through the store and notifies the library so
    /// the score column re-fetches.
    private func bindingForMetric() -> Binding<DisplayMetric> {
        Binding(
            get: { settings.displayMetric },
            set: { newValue in
                Task {
                    await settings.update(newValue)
                    onSettingsChanged()
                }
            }
        )
    }
}
