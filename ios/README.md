# muvi iOS

SwiftUI app. iOS 17.0+, Swift 6. Talks to the muvi backend at `http://127.0.0.1:8000`
(configurable in `Muvi/App/AppConfig.swift`).

## Prerequisites

- Xcode 15+ (Xcode 26 tested)
- `xcodegen` — install with `brew install xcodegen`

## Generate + open the project

The `.xcodeproj` is generated from `project.yml`, so it isn't checked into git.
Regenerate it any time you change `project.yml` or add source files:

```bash
cd ios
xcodegen generate
open Muvi.xcodeproj
```

Then in Xcode: pick an iPhone simulator, ⌘R to run.

## Running from the command line

```bash
cd ios
xcodebuild -project Muvi.xcodeproj -scheme Muvi \
  -sdk iphonesimulator -configuration Debug \
  -destination 'generic/platform=iOS Simulator' build
```

## Layout

```
Muvi/
  App/
    MuviApp.swift           entry point; hands out AuthStore via .environment
    AppConfig.swift         apiBaseURL
  Networking/
    APIClient.swift         async/await HTTP + JSON, reads token from Keychain
    APIError.swift          typed errors + FastAPI error-body decoder
    KeychainStore.swift     kSecClassGenericPassword-backed token store
  Auth/
    AuthAPI.swift           /auth/signup, /auth/login
    AuthStore.swift         @Observable state (currentUser, isAuthenticating, lastError)
    AuthGateView.swift      Log in / Sign up screen (segmented switch)
  LoggedInPlaceholderView.swift   temporary shell — replaced by library UI in task 7
```

## Backend

The app targets `http://127.0.0.1:8000`. `Info.plist` has
`NSAppTransportSecurity → NSAllowsLocalNetworking = true` so the plaintext
localhost connection is permitted.

Start the backend before signing in:

```bash
cd ../backend
.venv/bin/uvicorn app.main:app --reload
```
