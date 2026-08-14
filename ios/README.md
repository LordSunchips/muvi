# muvi iOS

SwiftUI app. iOS 17.0+, Swift 6, iPhone only, portrait only.

## Which backend it talks to

Resolved in [`Muvi/App/AppConfig.swift`](./Muvi/App/AppConfig.swift), first match wins:

1. `MUVI_API_BASE_URL` in the process environment (an Xcode scheme env var)
2. `MUVI_API_BASE_URL` in Info.plist
3. The compiled-in default — `http://127.0.0.1:8000` in **Debug**, the Render URL in **Release**

So simulator work runs against a local server, and a build installed on a phone runs against
production. `Info.plist` sets `NSAppTransportSecurity → NSAllowsLocalNetworking` so the plaintext
localhost connection is permitted; production is HTTPS.

## Prerequisites

- Xcode 15+ (Xcode 26 tested)
- `xcodegen` — `brew install xcodegen`

## Generate + run

The `.xcodeproj` is generated from `project.yml` and isn't checked into git. Regenerate it after
changing `project.yml` or adding source files:

```bash
cd ios
xcodegen generate
open Muvi.xcodeproj
```

Pick an iPhone simulator and ⌘R. For Debug builds, start the backend first:

```bash
cd ../backend
uv run uvicorn app.main:app --reload
```

To install on a physical phone, see [DEVICE.md](./DEVICE.md).

## Building from the command line

```bash
cd ios
xcodebuild -scheme Muvi -configuration Debug \
  -destination 'generic/platform=iOS Simulator' build
```

Swap `-configuration Release` to build the variant that targets production.

## Layout

```
Muvi/
  App/
    MuviApp.swift          entry point; hands out AuthStore via .environment
    AppConfig.swift        apiBaseURL resolution (see above)
  Networking/
    APIClient.swift        async/await HTTP + JSON, reads the token from the Keychain
    APIError.swift         typed errors + FastAPI error-body decoder
    KeychainStore.swift    kSecClassGenericPassword-backed token store
  Auth/
    AuthAPI.swift          /auth/signup, /auth/login, /auth/me (delete)
    AuthStore.swift        @Observable auth state
    AuthGateView.swift     log in / sign up
  Library/
    LibraryView.swift      ranked list, genre + bucket filters
    LibraryRow.swift       one row: poster, title, bucket badge, score
    LibraryStore.swift     @Observable library state
    LibraryAPI.swift       /library
  AddMovie/
    AddMovieView.swift     TMDB search + add
    TMDBAPI.swift          /tmdb/search, /tmdb/movie, /tmdb/genres
  Rank/
    RankFlowView.swift     drives the ranking flow
    WatchDetailsView.swift date + notes before ranking
    BucketPickerView.swift loved / fine / bad
    ComparisonView.swift   "which was better?" head-to-head
    RankResultView.swift   final score
    RankStore.swift        flow state
    RankAPI.swift          /rank/start, /rank/{id}/compare
    RankDTOs.swift
  MovieDetail/
    MovieDetailView.swift  score, genres, ranking history
    EditRankingView.swift  edit a logged watch
    MovieDetailStore.swift
    MovieDetailAPI.swift   /movies/{id}, /rankings/{id}
    MovieDetailDTOs.swift
  Settings/
    SettingsView.swift     score metric, log out, delete account, TMDB attribution
    SettingsStore.swift
    SettingsAPI.swift      /settings
  Shared/
    DTOs.swift             shared response types
    PosterView.swift       fixed 2:3 poster with placeholder
    TMDBImage.swift        poster path -> image.tmdb.org URL
    BucketBadge.swift      loved / fine / bad pill
```

Posters load directly from TMDB's CDN rather than through the backend.

## Signing

`DEVELOPMENT_TEAM` and `CODE_SIGN_STYLE` are pinned in `project.yml`, so a regenerated project is
already configured — the generated `.xcodeproj` is gitignored, and without pinning every
`xcodegen generate` would discard the team. Anyone building under a different Apple account needs
to override `DEVELOPMENT_TEAM`.
