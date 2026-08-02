import SwiftUI

/// Container that swaps between sign-in and sign-up. Shown when the user isn't authenticated.
struct AuthGateView: View {
    @State private var mode: Mode = .login

    enum Mode { case login, signup }

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Text("muvi")
                    .font(.system(size: 40, weight: .bold, design: .rounded))
                Text("your movies, ranked")
                    .foregroundStyle(.secondary)

                Picker("", selection: $mode) {
                    Text("Log in").tag(Mode.login)
                    Text("Sign up").tag(Mode.signup)
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)

                Group {
                    if mode == .login {
                        LoginView()
                    } else {
                        SignupView()
                    }
                }
            }
            .padding()
        }
    }
}

struct LoginView: View {
    @Environment(AuthStore.self) private var auth
    @State private var email = ""
    @State private var password = ""

    var body: some View {
        AuthFormView(
            email: $email,
            password: $password,
            actionTitle: "Log in",
            action: { await auth.login(email: email, password: password) }
        )
    }
}

struct SignupView: View {
    @Environment(AuthStore.self) private var auth
    @State private var email = ""
    @State private var password = ""

    var body: some View {
        AuthFormView(
            email: $email,
            password: $password,
            actionTitle: "Create account",
            passwordFooter: "At least 8 characters.",
            action: { await auth.signup(email: email, password: password) }
        )
    }
}

private struct AuthFormView: View {
    @Environment(AuthStore.self) private var auth
    @Binding var email: String
    @Binding var password: String
    let actionTitle: String
    var passwordFooter: String? = nil
    let action: () async -> Void

    var body: some View {
        VStack(spacing: 16) {
            TextField("email", text: $email)
                .textContentType(.emailAddress)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .keyboardType(.emailAddress)
                .padding()
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12))

            VStack(alignment: .leading, spacing: 4) {
                SecureField("password", text: $password)
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                if let footer = passwordFooter {
                    Text(footer)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .padding(.leading, 4)
                }
            }

            if let error = auth.lastError {
                Text(error)
                    .font(.footnote)
                    .foregroundStyle(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            Button {
                Task { await action() }
            } label: {
                if auth.isAuthenticating {
                    ProgressView().tint(.white)
                } else {
                    Text(actionTitle).fontWeight(.semibold)
                }
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color.accentColor)
            .foregroundStyle(.white)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .disabled(email.isEmpty || password.isEmpty || auth.isAuthenticating)
        }
    }
}
