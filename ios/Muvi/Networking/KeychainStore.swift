import Foundation
import Security

/// Stores the muvi access token in the iOS Keychain (thread-safe by virtue of Keychain APIs).
///
/// Backed by `kSecClassGenericPassword` scoped to the app's bundle id + a fixed account name.
/// Reading/writing `token = nil` deletes the item.
final class KeychainStore: Sendable {
    static let shared = KeychainStore(service: "com.muvi.app", account: "access_token")

    let service: String
    let account: String

    init(service: String, account: String) {
        self.service = service
        self.account = account
    }

    var token: String? {
        get { readString() }
        set {
            if let value = newValue {
                writeString(value)
            } else {
                delete()
            }
        }
    }

    private func readString() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    private func writeString(_ value: String) {
        let data = Data(value.utf8)
        let base: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        let attributes: [String: Any] = [kSecValueData as String: data]
        let status = SecItemUpdate(base as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var addQuery = base
            addQuery[kSecValueData as String] = data
            SecItemAdd(addQuery as CFDictionary, nil)
        }
    }

    private func delete() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        SecItemDelete(query as CFDictionary)
    }
}
