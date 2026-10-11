import Foundation
import Combine

enum ClientError: LocalizedError {
    case message(String)
    var errorDescription: String? { if case .message(let text) = self { return text }; return nil }
}
struct WorkItem: Decodable, Identifiable { let id: String; let title: String; let state: String; let priority: String; let due: String? }
struct Conversation: Decodable, Identifiable { let id: String; let title: String; let model: String }
struct Notice: Decodable, Identifiable { let id: String; let title: String; let status: String; let error: String? }
struct Operations: Decodable { let notifications: [Notice] }
struct ChatLine: Identifiable { let id = UUID(); let role: String; var text: String }
final class NoRedirects: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
}
@MainActor final class SoloClient: ObservableObject {
    @Published var server = UserDefaults.standard.string(forKey:"soloos.server") ?? "https://phamvanthu.com"
    @Published var connected = false
    @Published var busy = false
    @Published var error = ""
    @Published var tasks: [WorkItem] = []
    @Published var conversations: [Conversation] = []
    @Published var notices: [Notice] = []
    @Published var lines: [ChatLine] = []
    @Published var conversation = "default"
    private var token = ""
    private var generation = UUID()
    private var chatTask: Task<Void,Never>?
    private let session = URLSession(configuration:.ephemeral, delegate:NoRedirects(), delegateQueue:nil)
    init() { if let saved = Credentials.read(server:server) { token=saved; connected=true } }
    static func baseURL(_ address: String) throws -> URL {
        guard let url=URL(string:address), url.scheme=="https", let host=url.host, !host.isEmpty, url.user==nil, url.password==nil, url.query==nil, url.fragment==nil, url.path.isEmpty || url.path=="/" else { throw ClientError.message("Nhập địa chỉ HTTPS gốc, không kèm đường dẫn hoặc tài khoản.") }
        return url
    }
    func request(_ path: String, method: String="GET", body: [String:Any]?=nil, anonymous: Bool=false) throws -> URLRequest {
        let base=try Self.baseURL(server)
        var request=URLRequest(url:base.appendingPathComponent(path))
        request.httpMethod=method; request.timeoutInterval=180
        request.setValue("application/json",forHTTPHeaderField:"Content-Type")
        if !anonymous { request.setValue("Bearer "+token,forHTTPHeaderField:"Authorization") }
        if let body { request.httpBody=try JSONSerialization.data(withJSONObject:body) }
        return request
    }
    func data(_ path:String,method:String="GET",body:[String:Any]?=nil,anonymous:Bool=false) async throws -> Data {
        let (data,response)=try await session.data(for:request(path,method:method,body:body,anonymous:anonymous))
        guard let http=response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            let message=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any]
            throw ClientError.message(message?["detail"] as? String ?? "Yêu cầu chưa hoàn tất. Kiểm tra kết nối và quyền thiết bị.")
        }
        return data
    }
    func pair(code:String) async {
        busy=true; error=""; defer{busy=false}
        do {
            let base=try Self.baseURL(server).absoluteString.trimmingCharacters(in:CharacterSet(charactersIn:"/"))
            server=base
            let result=try await data("api/devices/redeem",method:"POST",body:["code":code.trimmingCharacters(in:.whitespacesAndNewlines)],anonymous:true)
            guard let value=try JSONSerialization.jsonObject(with:result) as? [String:Any],let credential=value["token"] as? String else {throw ClientError.message("Phản hồi ghép thiết bị không hợp lệ.")}
            try Credentials.save(credential,server:server);token=credential
            UserDefaults.standard.set(server,forKey:"soloos.server");connected=true
            await refresh()
        } catch { self.error=error.localizedDescription }
    }
    func refresh() async {
        error=""
        do {
            tasks=try JSONDecoder().decode([WorkItem].self,from:await data("api/tasks"))
            conversations=try JSONDecoder().decode([Conversation].self,from:await data("api/workspace/sessions"))
            notices=try JSONDecoder().decode(Operations.self,from:await data("api/operations")).notifications
        } catch {self.error=error.localizedDescription}
    }
    func createTask(_ title:String) async -> Bool { do {_ = try await data("api/tasks",method:"POST",body:["title":title]);await refresh();return true}catch{self.error=error.localizedDescription;return false} }
    func move(_ item:WorkItem,to state:String) async {do{_ = try await data("api/tasks/"+item.id,method:"PATCH",body:["state":state]);await refresh()}catch{self.error=error.localizedDescription}}
    func loadChat() async {
        stop()
        let currentConversation=conversation
        let turn=generation
        do {let payload=try await data("api/conversations/"+currentConversation);guard generation==turn else{return};let values=(try JSONSerialization.jsonObject(with:payload)) as? [[String:Any]] ?? [];lines=values.map{ChatLine(role:$0["role"] as? String ?? "assistant",text:$0["content"] as? String ?? "")}}catch{self.error=error.localizedDescription}
    }
    func send(_ message:String) {
        guard !busy,!message.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty else{return}
        busy=true;error="";lines.append(ChatLine(role:"user",text:message));lines.append(ChatLine(role:"assistant",text:""))
        let turn=UUID(); generation=turn
        chatTask=Task {
            defer{if generation==turn {busy=false}}
            do {
                let library="root = Stack([t]); t = Text(\"Your complete answer\"). Available components: Stack(children), Text(content). Use JSON quoted strings. No other components."
                let request=try request("api/chat",method:"POST",body:["message":message,"conversation":conversation,"model":"solo-default","ui_prompt":library])
                let (bytes,response)=try await session.bytes(for:request)
                guard let http=response as? HTTPURLResponse,http.statusCode==200 else{throw ClientError.message("Không mở được luồng AI. Kiểm tra quyền chat và nguồn AI.")}
                var done=false
                for try await line in bytes.lines {
                    try Task.checkCancellation()
                    guard generation==turn else{return}
                    guard line.hasPrefix("data: "), let data=line.dropFirst(6).data(using:.utf8),let event=try JSONSerialization.jsonObject(with:data) as? [String:Any] else{continue}
                    if event["type"] as? String == "token",let text=event["text"] as? String {lines[lines.count-1].text += text}
                    if event["type"] as? String == "error" {throw ClientError.message(event["message"] as? String ?? "AI chưa hoàn tất.")}
                    if event["type"] as? String == "confirmation" {self.error="Có thao tác chờ duyệt trên SoloOS web."}
                    if event["type"] as? String == "done" {done=true;break}
                }
                if !done {throw ClientError.message("Luồng AI kết thúc trước khi hoàn tất.")}
            } catch is CancellationError {} catch {if generation==turn {self.error=error.localizedDescription}}
        }
    }
    func stop(){generation=UUID();chatTask?.cancel();chatTask=nil;busy=false}
    func disconnect() async {
        stop()
        do {_ = try await data("api/devices/self",method:"DELETE")}catch{self.error="Đã xóa đăng nhập trên máy. Nếu máy chủ chưa thu hồi, hãy thu hồi thiết bị trên web."}
        Credentials.remove(server:server);token="";connected=false;tasks=[];notices=[];lines=[]
    }
}
