import XCTest
@testable import SoloOS
final class ClientTests:XCTestCase {
    @MainActor func testOnlyExplicitHTTPSOrigin() throws {
        XCTAssertEqual(try SoloClient.baseURL("https://phamvanthu.com").host,"phamvanthu.com")
        for url in ["http://phamvanthu.com","https://user:password@example.com","https://example.com/path","https://example.com?token=x"] {XCTAssertThrowsError(try SoloClient.baseURL(url))}
    }
    func testRenderingDoesNotExecuteMarkup() {
        XCTAssertEqual(readableText(#"root = Stack([a]); a = Text("Xin chào\n<script>test</script>")"#),"Xin chào\n<script>test</script>")
    }
}
