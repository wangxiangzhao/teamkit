import SwiftUI

@main
struct SmokeApp: App {
    @State private var expanded = false

    var body: some Scene {
        WindowGroup {
            VStack {
                Button(expanded ? "Hide details" : "Show details") {
                    withAnimation(.easeInOut(duration: 0.25)) {
                        expanded.toggle()
                    }
                }
                .accessibilityIdentifier("toggle-details")

                if expanded {
                    Text("Details are visible")
                        .accessibilityIdentifier("details")
                        .transition(.opacity)
                }
            }
        }
    }
}
