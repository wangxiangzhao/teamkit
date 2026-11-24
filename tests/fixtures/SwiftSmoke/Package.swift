// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "TeamKitSmoke",
    platforms: [.macOS(.v13), .iOS(.v17)],
    products: [.library(name: "TeamKitSmoke", targets: ["TeamKitSmoke"])],
    targets: [
        .target(name: "TeamKitSmoke"),
        .testTarget(name: "TeamKitSmokeTests", dependencies: ["TeamKitSmoke"])
    ]
)
