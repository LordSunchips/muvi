import Foundation

/// Thin async/await HTTP client for the muvi backend.
///
/// Reads the bearer token from ``KeychainStore`` on each request so token changes are picked up
/// without holding a stale copy. A 401 clears the stored token and raises ``APIError/unauthorized``.
struct APIClient {
    let baseURL: URL
    let session: URLSession
    let tokenStore: KeychainStore

    init(
        baseURL: URL = AppConfig.apiBaseURL,
        session: URLSession = .shared,
        tokenStore: KeychainStore = .shared
    ) {
        self.baseURL = baseURL
        self.session = session
        self.tokenStore = tokenStore
    }

    private static let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let raw = try container.decode(String.self)
            if let date = flexibleDate(from: raw) { return date }
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Unrecognized date: \(raw)")
        }
        return d
    }()

    private static let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()

    /// Parses the shapes the backend emits: ISO8601 with or without fractional seconds and with
    /// or without a timezone suffix. Naive timestamps are interpreted as UTC.
    nonisolated(unsafe) private static let iso8601WithFractional: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    nonisolated(unsafe) private static let iso8601Plain: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    private static let naiveFormatters: [DateFormatter] = {
        let patterns = [
            "yyyy-MM-dd'T'HH:mm:ss.SSSSSS",
            "yyyy-MM-dd'T'HH:mm:ss.SSS",
            "yyyy-MM-dd'T'HH:mm:ss",
            "yyyy-MM-dd",
        ]
        return patterns.map { pattern in
            let f = DateFormatter()
            f.locale = Locale(identifier: "en_US_POSIX")
            f.timeZone = TimeZone(identifier: "UTC")
            f.dateFormat = pattern
            return f
        }
    }()

    private static func flexibleDate(from string: String) -> Date? {
        if let d = iso8601WithFractional.date(from: string) { return d }
        if let d = iso8601Plain.date(from: string) { return d }
        for f in naiveFormatters {
            if let d = f.date(from: string) { return d }
        }
        return nil
    }

    // MARK: - Request builders

    private func makeRequest(
        method: String,
        path: String,
        query: [URLQueryItem] = [],
        body: Data? = nil
    ) throws -> URLRequest {
        guard var components = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false)
        else { throw APIError.invalidResponse }
        if !query.isEmpty {
            components.queryItems = query
        }
        guard let url = components.url else { throw APIError.invalidResponse }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if body != nil {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = body
        }
        if let token = tokenStore.token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    // MARK: - Public verbs

    func get<Response: Decodable>(_ path: String, query: [URLQueryItem] = []) async throws -> Response {
        try await send(try makeRequest(method: "GET", path: path, query: query))
    }

    func post<Body: Encodable, Response: Decodable>(_ path: String, body: Body) async throws -> Response {
        let data = try Self.encoder.encode(body)
        return try await send(try makeRequest(method: "POST", path: path, body: data))
    }

    /// Escape hatch for callers that need to encode the body with a bespoke encoder
    /// (e.g. plain-date fields).
    func postRaw<Response: Decodable>(_ path: String, body: Data) async throws -> Response {
        try await send(try makeRequest(method: "POST", path: path, body: body))
    }

    func patch<Body: Encodable, Response: Decodable>(_ path: String, body: Body) async throws -> Response {
        let data = try Self.encoder.encode(body)
        return try await send(try makeRequest(method: "PATCH", path: path, body: data))
    }

    func delete(_ path: String) async throws {
        _ = try await sendRaw(try makeRequest(method: "DELETE", path: path))
    }

    // MARK: - Send + decode

    private func send<Response: Decodable>(_ request: URLRequest) async throws -> Response {
        let data = try await sendRaw(request)
        if Response.self == EmptyResponse.self { return EmptyResponse() as! Response }
        do {
            return try Self.decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    @discardableResult
    private func sendRaw(_ request: URLRequest) async throws -> Data {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.transport(error)
        }
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        switch http.statusCode {
        case 200..<300:
            return data
        case 401:
            tokenStore.token = nil
            NotificationCenter.default.post(name: .muviSessionExpired, object: nil)
            throw APIError.unauthorized
        default:
            let detail = try? Self.decoder.decode(APIErrorBody.self, from: data).detail?.display
            throw APIError.http(status: http.statusCode, detail: detail)
        }
    }
}

struct EmptyResponse: Decodable {}

extension Notification.Name {
    /// Fired by ``APIClient`` when a 401 clears the stored token. Observed by ``AuthStore`` to
    /// drop the app back to the login screen.
    static let muviSessionExpired = Notification.Name("com.muvi.sessionExpired")
}
