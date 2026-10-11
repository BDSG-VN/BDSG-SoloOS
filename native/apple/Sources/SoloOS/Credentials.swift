import Foundation
import Security

enum Credentials {
    static let service = "vn.bdsg.soloos.device"
    static func query(_ server: String) -> [String: Any] {
        [kSecClass as String:kSecClassGenericPassword, kSecAttrService as String:service, kSecAttrAccount as String:server]
    }
    static func save(_ token: String, server: String) throws {
        var item = query(server)
        SecItemDelete(item as CFDictionary)
        item[kSecValueData as String] = Data(token.utf8)
        item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        let result = SecItemAdd(item as CFDictionary, nil)
        guard result == errSecSuccess else { throw ClientError.message("Không lưu được thông tin vào Keychain (\(result)).") }
    }
    static func read(server: String) -> String? {
        var item = query(server)
        item[kSecReturnData as String] = true
        item[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        guard SecItemCopyMatching(item as CFDictionary, &result) == errSecSuccess, let data = result as? Data else { return nil }
        return String(data:data, encoding:.utf8)
    }
    static func remove(server: String) { SecItemDelete(query(server) as CFDictionary) }
}
