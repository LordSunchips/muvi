import Foundation

enum APIError: LocalizedError {
    case invalidResponse
    case unauthorized
    case http(status: Int, detail: String?)
    case decoding(Error)
    case transport(Error)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "The server returned an unexpected response."
        case .unauthorized:
            return "Your session has expired. Please log in again."
        case .http(_, let detail):
            return detail ?? "The request failed."
        case .decoding(let error):
            return "Couldn't parse the server response: \(error.localizedDescription)"
        case .transport(let error):
            return "Network error: \(error.localizedDescription)"
        }
    }
}

/// FastAPI's default error envelope: `{ "detail": "..." }` or a validation-error list.
struct APIErrorBody: Decodable {
    let detail: DetailValue?

    enum DetailValue: Decodable {
        case string(String)
        case list([ValidationItem])

        init(from decoder: Decoder) throws {
            let container = try decoder.singleValueContainer()
            if let s = try? container.decode(String.self) {
                self = .string(s)
            } else if let items = try? container.decode([ValidationItem].self) {
                self = .list(items)
            } else {
                self = .string("")
            }
        }

        var display: String {
            switch self {
            case .string(let s): return s
            case .list(let items): return items.map(\.msg).joined(separator: "; ")
            }
        }
    }

    struct ValidationItem: Decodable {
        let msg: String
    }
}
