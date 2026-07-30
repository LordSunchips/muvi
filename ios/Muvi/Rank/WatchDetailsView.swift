import SwiftUI

/// First step of the logWatch flow: capture the viewing date and optional note before ranking.
struct WatchDetailsView: View {
    let movie: LibraryMovieDTO
    @Binding var watchedOn: Date
    @Binding var note: String
    let onContinue: () -> Void

    var body: some View {
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
                Section("When did you watch it?") {
                    DatePicker("Date", selection: $watchedOn, in: ...Date(), displayedComponents: .date)
                }
                Section("Notes (optional)") {
                    TextField("What did you think?", text: $note, axis: .vertical)
                        .lineLimit(3...6)
                }
            }
            .scrollDisabled(true)
            .frame(height: 340)

            Button(action: onContinue) {
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
    }
}
