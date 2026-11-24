import XCTest
@testable import TeamKitSmoke

final class TeamKitSmokeTests: XCTestCase {
    func testArithmetic() {
        XCTAssertEqual(TeamKitSmoke.sum(2, 3), 5)
        XCTAssertEqual(TeamKitSmoke.greeting(), "TeamKit")
    }
}
