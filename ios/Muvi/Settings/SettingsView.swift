import SwiftUI

struct SettingsView: View {
    @Environment(AuthStore.self) private var auth
    @Environment(\.dismiss) private var dismiss
    @State private var settings = SettingsStore()
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
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
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
