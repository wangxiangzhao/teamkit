import XCTest

final class SmokeUITests: XCTestCase {
    func testDetailsCanBeShownAndHidden() {
        let app = XCUIApplication()
        app.launch()
        let toggle = app.buttons["toggle-details"]
        let details = app.staticTexts["details"]
        XCTAssertFalse(details.exists)
        XCTAssertTrue(toggle.waitForExistence(timeout: 5))
        toggle.tap()
        XCTAssertTrue(details.waitForExistence(timeout: 5))

        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Details visible"
        screenshot.lifetime = .keepAlways
        add(screenshot)

        toggle.tap()
        let hidden = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: details)
        XCTAssertEqual(XCTWaiter.wait(for: [hidden], timeout: 5), .completed)
    }
}
