import SwiftUI

struct AddWatchView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var watchedOn: Date = .now
    @State private var note: String = ""
    @State private var isSaving = false

    let onSave: (Date, String?) async -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section("When did you watch it?") {
                    DatePicker("Date", selection: $watchedOn, in: ...Date(), displayedComponents: .date)
                }
                Section("Notes (optional)") {
                    TextField("What did you think?", text: $note, axis: .vertical)
                        .lineLimit(3...6)
                }
            }
            .navigationTitle("Log a watch")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task {
                            isSaving = true
                            let trimmed = note.trimmingCharacters(in: .whitespacesAndNewlines)
                            await onSave(watchedOn, trimmed.isEmpty ? nil : trimmed)
                            isSaving = false
                            dismiss()
                        }
                    } label: {
                        if isSaving { ProgressView() } else { Text("Save").fontWeight(.semibold) }
                    }
                    .disabled(isSaving)
                }
            }
        }
    }
}
