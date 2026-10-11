import SwiftUI

@main struct SoloOSApp: App {
    @StateObject private var client=SoloClient()
    var body: some Scene {
        WindowGroup { RootView().environmentObject(client).frame(minWidth:320,minHeight:500) }
        #if os(macOS)
        MenuBarExtra("SoloOS",systemImage:"sparkles") {
            Button("Làm mới trạng thái"){Task{await client.refresh()}}
            Text(client.connected ? "Đã ghép với SoloOS" : "Chưa ghép thiết bị")
            if let base=try? SoloClient.baseURL(client.server) {Link("Mở quản trị web",destination:base.appendingPathComponent("admin"))}
        }
        #endif
    }
}
struct RootView: View {
    @EnvironmentObject var client:SoloClient
    @State private var code=""
    var body: some View {
        VStack(spacing:12) {
            if !client.error.isEmpty { Text(client.error).foregroundStyle(.orange).padding().accessibilityLabel("Thông báo: "+client.error) }
            if client.connected {
                TabView {
                    ChatView().tabItem{Label("AI Studio",systemImage:"bubble.left.and.bubble.right")}
                    WorkView().tabItem{Label("Công việc",systemImage:"checklist")}
                    List(client.notices){notice in VStack(alignment:.leading,spacing:6){Text(notice.title).font(.headline);Text(notice.status).font(.caption);if let error=notice.error {Text(error).foregroundStyle(.orange)}}}.tabItem{Label("Vận hành",systemImage:"bell")}
                    VStack(spacing:20){Text(client.server).textSelection(.enabled);Text("Quyền được quản lý trong Thiết bị & ứng dụng trên web.");Button("Làm mới"){Task{await client.refresh()}};Button("Ngắt thiết bị",role:.destructive){Task{await client.disconnect()}}}.padding().tabItem{Label("Thiết bị",systemImage:"gearshape")}
                }.task{await client.refresh()}
            } else {
                VStack(alignment:.leading,spacing:18){Text("BDSG SoloOS").font(.largeTitle.bold());Text("Ghép với không gian riêng của bạn").font(.title3);TextField("Máy chủ HTTPS",text:$client.server).textFieldStyle(.roundedBorder);SecureField("Mã ghép dùng một lần",text:$code).textFieldStyle(.roundedBorder);Text("Trên web, vào Thiết bị & ứng dụng để tạo mã. Mã hết hạn sau 5 phút.").foregroundStyle(.secondary);Button("Ghép thiết bị"){let value=code;code="";Task{await client.pair(code:value)}}.buttonStyle(.borderedProminent).disabled(client.busy||code.isEmpty)}.padding(28).frame(maxWidth:520)
            }
        }.tint(Color(red:0.3,green:0.65,blue:0.4))
    }
}
struct WorkView: View {
    @EnvironmentObject var client:SoloClient
    @State private var title=""
    var body: some View {
        VStack {
            HStack{TextField("Công việc mới",text:$title).textFieldStyle(.roundedBorder);Button("Thêm"){let value=title;Task{if await client.createTask(value),title==value{title=""}}}.disabled(title.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty)}.padding()
            List(client.tasks){item in VStack(alignment:.leading,spacing:8){Text(item.title).font(.headline);Text(item.priority+(item.due.map{" · "+$0} ?? "")).font(.caption).foregroundStyle(.secondary);Picker("Trạng thái",selection:Binding(get:{item.state},set:{value in Task{await client.move(item,to:value)}})){Text("Cần làm").tag("todo");Text("Đang làm").tag("doing");Text("Hoàn tất").tag("done")}.pickerStyle(.segmented)}}
        }
    }
}
struct ChatView: View {
    @EnvironmentObject var client:SoloClient
    @State private var message=""
    var body: some View {
        VStack {
            Picker("Cuộc trò chuyện",selection:$client.conversation){ForEach(client.conversations){row in Text(row.title).tag(row.id)}}.disabled(client.busy).padding(.horizontal).onChange(of:client.conversation){_ in Task{await client.loadChat()}}
            ScrollViewReader{proxy in ScrollView{LazyVStack(alignment:.leading,spacing:18){ForEach(client.lines){line in VStack(alignment:.leading,spacing:6){Text(line.role=="user" ? "BẠN" : "SOLOOS").font(.caption).foregroundStyle(.secondary);Text(line.role=="user" ? line.text : readableText(line.text)).textSelection(.enabled)}.padding().frame(maxWidth:.infinity,alignment:.leading).background(Color.secondary.opacity(0.08)).clipShape(RoundedRectangle(cornerRadius:12)).id(line.id)}}.padding()}.onChange(of:client.lines.last?.text){_ in if let id=client.lines.last?.id{proxy.scrollTo(id,anchor:.bottom)}}}
            HStack(alignment:.bottom){TextField("Nhập yêu cầu…",text:$message,axis:.vertical).textFieldStyle(.roundedBorder).lineLimit(1...5);if client.busy{Button("Dừng"){client.stop()}}else{Button("Gửi"){let value=message;message="";client.send(value)}.disabled(message.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty)}}.padding()
        }.task{await client.loadChat()}
    }
}
func readableText(_ source:String)->String {
    let pattern=#"Text\s*\(\s*("(?:\\.|[^"\\])*")\s*\)"#
    guard let regex=try? NSRegularExpression(pattern:pattern) else{return source}
    let range=NSRange(source.startIndex...,in:source)
    let texts=regex.matches(in:source,range:range).compactMap{match->String? in guard let r=Range(match.range(at:1),in:source),let data=String(source[r]).data(using:.utf8) else{return nil};return try? JSONDecoder().decode(String.self,from:data)}
    return texts.isEmpty ? (source.isEmpty ? "Đang chờ phản hồi…" : "Đang nhận nội dung…") : texts.joined(separator:"\n\n")
}
