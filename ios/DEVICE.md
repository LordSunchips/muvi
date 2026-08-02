# Installing muvi on your iPhone

Uses free personal-team signing via Xcode. No paid Apple Developer account needed. Certificates
expire after 7 days; you re-run from Xcode weekly to refresh.

## One-time setup

1. **Deploy the backend** first (see `../backend/DEPLOY.md`). You need the production URL.
2. **Point the release build at prod.** In `Muvi/App/AppConfig.swift`, update the release URL:
   ```swift
   #else
   private static let defaultBaseURL = "https://YOUR-APP.fly.dev"
   #endif
   ```
   (Debug builds still target `127.0.0.1:8000` so simulator dev keeps working.)
3. **Sign into Xcode with your Apple ID.** Xcode → Settings → Accounts → “+” → Apple ID. You get a
   free "Personal Team" that can sign apps for your own devices.
4. **Trust your Mac on the iPhone.** Plug the phone in with a USB cable, unlock it, tap "Trust" when
   prompted, and enter the passcode.
5. **Enable Developer Mode on the iPhone** (iOS 16+): Settings → Privacy & Security → Developer
   Mode → On → phone restarts.

## Build + install

1. `cd ios && xcodegen generate` — regenerates the Xcode project from `project.yml`.
2. Open `ios/Muvi.xcodeproj` in Xcode.
3. Select the **Muvi** target in the sidebar → **Signing & Capabilities** tab.
   - Team: pick your Apple ID's Personal Team.
   - Bundle Identifier: `com.sunchips.muvi` (already set in `project.yml`).
     If Xcode complains it can't register the bundle ID, append something unique like
     `com.sunchips.muvi.<yourinitials>` — Personal Teams sometimes reject generic-looking IDs.
4. At the top of the Xcode window, pick your iPhone from the run-destination dropdown (it appears
   under "iOS Device" once the phone is connected and trusted).
5. Change scheme to **Release**: Product → Scheme → Edit Scheme → Run → Info → Build Configuration
   = Release. This makes the app hit your Fly URL instead of `127.0.0.1`.
6. **Command-R**. Xcode builds, installs, and launches on the phone.
7. First launch on the phone: iOS refuses to run apps from an untrusted developer. On the phone go
   to Settings → General → VPN & Device Management → Developer App → tap your Apple ID → Trust.
   Then relaunch.

## Wireless deploy after the first install

Once the phone appears in Xcode via USB you can enable Wi-Fi debugging: Xcode → Window → Devices
and Simulators → select your phone → check "Connect via network". After that, unplug and Command-R
works over Wi-Fi (both devices on the same network).

## When it stops working after 7 days

The provisioning profile Personal Team creates expires every 7 days. The app either fails to launch
or greys out on the home screen. Plug back into Xcode and Command-R — it re-signs and reinstalls.

## Troubleshooting

- **"Could not locate device support files"**: Xcode is missing the platform for your iOS version.
  Xcode → Settings → Platforms → download the matching iOS.
- **App fails to fetch on device but works in simulator**: your Fly URL is unreachable or the
  Release config still points at localhost. Check `AppConfig.swift`.
- **"No matching profiles found"**: In Signing & Capabilities, uncheck and re-check "Automatically
  manage signing".
