import SwiftUI

extension Bucket {
    var tint: Color {
        switch self {
        case .loved: return .green
        case .fine: return .yellow
        case .bad: return .red
        }
    }
}

/// Small colored pill showing the bucket name. Used on library rows and detail views.
struct BucketBadge: View {
    let bucket: Bucket

    var body: some View {
        Text(bucket.displayName)
            .font(.caption2.weight(.semibold))
            .textCase(.uppercase)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(bucket.tint.opacity(0.18), in: Capsule())
            .foregroundStyle(bucket.tint)
    }
}
