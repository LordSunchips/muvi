# Installing muvi on your iPhone

Signed with the paid Apple Developer Program account (team `8589WU98SC`). Provisioning profiles
last a year, so unlike free personal-team signing there's no weekly re-install.

Release builds talk to the production backend on Render; Debug builds talk to `127.0.0.1:8000`
so simulator work keeps running against a local server. The switch is the build configuration —
see step 4 below.

## One-time setup

1. **Sign into Xcode with the developer account.** Xcode → Settings → Accounts → "+" → Apple ID.
2. **Trust your Mac on the iPhone.** Plug the phone in over USB, unlock it, tap "Trust", enter the
   passcode.
3. **Enable Developer Mode on the iPhone** (iOS 16+): Settings → Privacy & Security → Developer
   Mode → On. The phone restarts.

You don't need to pick a team in Xcode. `DEVELOPMENT_TEAM` and `CODE_SIGN_STYLE` are set in
[`project.yml`](./project.yml), so a regenerated project comes out already configured — the
`.xcodeproj` is generated and gitignored, and pinning them there is what stops `xcodegen generate`
from discarding the choice.

## Build + install

```bash
cd ios
xcodegen generate
open Muvi.xcodeproj
```

1. Pick your iPhone from the run-destination dropdown. It appears under "iOS Device" once the
   phone is connected, unlocked and trusted.
2. Switch the scheme to **Release**: Product → Scheme → Edit Scheme → Run → Info → Build
   Configuration = Release. This is what points the app at the Render backend instead of
   `127.0.0.1` — see the `#if DEBUG` in [`Muvi/App/AppConfig.swift`](./Muvi/App/AppConfig.swift).
3. **⌘R.** Xcode builds, installs and launches.
4. First launch of a build from a new certificate: Settings → General → VPN & Device Management →
   Developer App → tap the account → Trust. Then relaunch.

## Wireless deploy

Once the phone has been connected over USB: Xcode → Window → Devices and Simulators → select the
phone → check "Connect via network". Unplug, and ⌘R works over Wi-Fi with both devices on the same
network.

## Troubleshooting

**Everything fails to load, and it isn't the phone.** Check the backend directly:

```bash
curl -s https://muvi-backend.onrender.com/health
```

That returns the running commit, so it also tells you which build is deployed. `/health` touches
no database, so a healthy response there does **not** mean the API is working — test a
database-backed route too:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://muvi-backend.onrender.com/auth/login \
  -H 'Content-Type: application/json' -d '{"email":"nobody@example.com","password":"whatever"}'
```

`401` means the database is reachable and the credentials were simply wrong — that's a healthy
API. `500` means the database isn't reachable. That combination — `/health` green while every
real route 500s — is what a dropped Turso connection looks like; see `pool_options` in
[`../backend/app/db.py`](../backend/app/db.py). Restarting the Render service clears it.

**Suddenly logged out, or a stored session stops working.** Access tokens carry `User.public_id`.
Anything that changes how tokens are minted invalidates every existing one, and the app drops to
the auth gate. Log in again.

**"Could not locate device support files".** Xcode is missing the platform for your iOS version:
Xcode → Settings → Platforms → download the matching iOS.

**"No matching profiles found".** In Signing & Capabilities, uncheck and re-check "Automatically
manage signing". If it persists, confirm the bundle ID `com.sunchips.muvi` is still registered
under the team in the developer portal.

**App runs but can't reach the backend on device while the simulator works.** The simulator was
probably on a Debug build hitting localhost. Confirm the scheme is set to Release (step 2 above).
