// swift-tools-version: 5.9
import PackageDescription
let package = Package(name: "SoloOS", platforms: [.macOS(.v13), .iOS(.v16)], products: [.executable(name: "SoloOS", targets: ["SoloOS"])], targets: [.executableTarget(name: "SoloOS"), .testTarget(name: "SoloOSTests", dependencies: ["SoloOS"])])
