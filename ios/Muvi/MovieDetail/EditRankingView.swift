import SwiftUI

/// Sheet for editing a logged ranking's captured watch metadata (note + date). Bucket and score
/// are intentionally not editable here — changing those means re-running the rank flow so the
/// algorithm can re-place the movie against its peers.
struct EditRankingView: View {
    let ranking: RankingDTO
    /// Called with (note, watchedOn, clearWatchedOn). `clearWatchedOn == true` means "the user
    /// wants to drop the date entirely"; `false` + `nil` means "leave date as-is".
    let onSave: (String?, Date?, Bool) async -> Bool

    @Environment(\.dismiss) private var dismiss

    @State private var note: String
    @State private var includeDate: Bool
    @State private var draftDate: Date
    @State private var isSaving = false
    @FocusState private var noteFocused: Bool

    init(ranking: RankingDTO, onSave: @escaping (String?, Date?, Bool) async -> Bool) {
        self.ranking = ranking
        self.onSave = onSave
        _note = State(initialValue: ranking.note ?? "")
        _includeDate = State(initialValue: ranking.watchedOn != nil)
        _draftDate = State(initialValue: ranking.watchedOn ?? Date())
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    Form {
                        Section {
                            Toggle("I remember when", isOn: $includeDate)
                            if includeDate {
                                DatePicker("Date", selection: $draftDate, in: ...Date(), displayedComponents: .date)
                            }
                        } header: {
                            Text("Watched on")
                        } footer: {
                            Text(includeDate
                                 ? "Kept in the history and used by mean/median metrics."
                                 : "Turn off to log this as a plain watch without a date.")
                        }
                        Section("Notes") {
                            TextField("What did you think?", text: $note, axis: .vertical)
                                .lineLimit(3...10)
                                .focused($noteFocused)
                                .submitLabel(.done)
                                .onSubmit { noteFocused = false }
                        }
                    }
                    .scrollDisabled(true)
                    .frame(minHeight: 380)
                }
                .padding(.bottom, 32)
            }
            .scrollDismissesKeyboard(.interactively)
            .navigationTitle("Edit watch")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") { dismiss() }
                        .disabled(isSaving)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Save") { Task { await save() } }
                        .fontWeight(.semibold)
                        .disabled(isSaving)
                }
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Done") { noteFocused = false }
                }
            }
            .overlay {
                if isSaving {
                    Color.black.opacity(0.1).ignoresSafeArea()
                    ProgressView().controlSize(.large)
                }
            }
        }
    }

    private func save() async {
        isSaving = true
        defer { isSaving = false }
        let trimmed = note.trimmingCharacters(in: .whitespacesAndNewlines)
        let noteToSend: String? = trimmed.isEmpty ? nil : trimmed
        let watchedToSend: Date? = includeDate ? draftDate : nil
        let clearDate = !includeDate
        let ok = await onSave(noteToSend, watchedToSend, clearDate)
        if ok { dismiss() }
    }
}
