import SwiftUI

/// First step of the logWatch flow: capture the (optional) viewing date and optional note before
/// ranking. The date starts off enabled with today's value; a toggle lets the user drop the date
/// entirely if they can't remember when they watched it.
struct WatchDetailsView: View {
    let movie: LibraryMovieDTO
    @Binding var watchedOn: Date?
    @Binding var note: String
    let onContinue: () -> Void

    @FocusState private var noteFocused: Bool
    @State private var includeDate: Bool
    @State private var draftDate: Date

    init(movie: LibraryMovieDTO, watchedOn: Binding<Date?>, note: Binding<String>, onContinue: @escaping () -> Void) {
        self.movie = movie
        self._watchedOn = watchedOn
        self._note = note
        self.onContinue = onContinue
        _includeDate = State(initialValue: watchedOn.wrappedValue != nil)
        _draftDate = State(initialValue: watchedOn.wrappedValue ?? Date())
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                VStack(spacing: 8) {
                    PosterView(path: movie.posterPath, width: 120)
                    Text(movie.title)
                        .font(.title3.weight(.semibold))
                        .multilineTextAlignment(.center)
                    if let year = movie.year {
                        Text(String(year))
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.top, 8)

                Form {
                    Section {
                        Toggle("I remember when", isOn: $includeDate)
                        if includeDate {
                            DatePicker("Date", selection: $draftDate, in: ...Date(), displayedComponents: .date)
                        }
                    } header: {
                        Text("When did you watch it?")
                    } footer: {
                        Text(includeDate
                             ? "The date shows up in your history and helps mean/median metrics."
                             : "Leave it off and the entry logs as a plain watch without a date.")
                    }
                    Section("Notes (optional)") {
                        TextField("What did you think?", text: $note, axis: .vertical)
                            .lineLimit(3...10)
                            .focused($noteFocused)
                            .submitLabel(.done)
                            .onSubmit { noteFocused = false }
                    }
                }
                .scrollDisabled(true)
                .frame(minHeight: 380)

                Button(action: continueTapped) {
                    Text("Continue to rank").fontWeight(.semibold)
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.accentColor)
                .foregroundStyle(.white)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .padding(.horizontal)

                Spacer(minLength: 0)
            }
            .padding(.bottom, 32)
        }
        .scrollDismissesKeyboard(.interactively)
        .toolbar {
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("Done") { noteFocused = false }
            }
        }
        .onChange(of: includeDate) { _, on in
            watchedOn = on ? draftDate : nil
        }
        .onChange(of: draftDate) { _, newValue in
            if includeDate { watchedOn = newValue }
        }
    }

    private func continueTapped() {
        watchedOn = includeDate ? draftDate : nil
        noteFocused = false
        onContinue()
    }
}
