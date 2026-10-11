package vn.bdsg.soloos;

import android.app.Activity;
import android.os.Bundle;
import android.text.InputType;
import android.widget.*;
import java.net.URI;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import javax.net.ssl.HttpsURLConnection;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
 private final ExecutorService executor=Executors.newSingleThreadExecutor();
 private LinearLayout root,content;private TextView status;private Vault vault;
 private String server="https://phamvanthu.com",token="";private volatile boolean stopped=false;private volatile HttpsURLConnection active;private int screen=0;
 interface Work {void run() throws Exception;}
 @Override public void onCreate(Bundle state){super.onCreate(state);vault=new Vault(this);try{String[] saved=vault.read();if(saved!=null){server=saved[0];token=saved[1];}}catch(Exception e){token="";}show();}
 private TextView text(String value,int size){TextView view=new TextView(this);view.setText(value);view.setTextSize(size);view.setPadding(0,12,0,12);return view;}
 private EditText input(String hint,boolean secret){EditText view=new EditText(this);view.setHint(hint);view.setSingleLine(true);if(secret)view.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);return view;}
 private void button(LinearLayout parent,String title,Runnable action){Button button=new Button(this);button.setText(title);button.setOnClickListener(v->action.run());parent.addView(button);}
 private void run(Work work){status.setText("Đang xử lý…");executor.execute(()->{try{work.run();}catch(Exception e){ui(()->status.setText(stopped?"Đã dừng.":e.getMessage()));}});}
 private void ui(Runnable action){runOnUiThread(()->{if(!isDestroyed()&&!isFinishing())action.run();});}
 private void show(){
  ScrollView scroll=new ScrollView(this);root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(28,32,28,28);scroll.addView(root);setContentView(scroll);
  root.addView(text("BDSG SoloOS",28));status=text("",14);root.addView(status);
  if(token.isEmpty()){
   root.addView(text("Ghép thiết bị bằng mã dùng một lần trong mục Thiết bị & ứng dụng trên web.",16));EditText address=input("Máy chủ HTTPS",false);address.setText(server);root.addView(address);EditText code=input("Mã ghép thiết bị",true);root.addView(code);
   button(root,"Ghép thiết bị",()->{String host=address.getText().toString().trim(),pair=code.getText().toString().trim();code.setText("");run(()->{URI uri=new URI(host);if(!"https".equals(uri.getScheme())||uri.getHost()==null||uri.getUserInfo()!=null||uri.getQuery()!=null||uri.getFragment()!=null||!(uri.getPath().isEmpty()||uri.getPath().equals("/")))throw new Exception("Nhập địa chỉ HTTPS gốc.");server=host.replaceAll("/$","");JSONObject response=new JSONObject(request("/api/devices/redeem","POST",new JSONObject().put("code",pair)));String credential=response.getString("token");vault.save(server,credential);token=credential;ui(this::show);});});return;
  }
  LinearLayout nav=new LinearLayout(this);root.addView(nav);
  for(int i=0;i<3;i++){final int index=i;button(nav,new String[]{"AI","Công việc","Thiết bị"}[i],()->{stop();screen=index;show();});}
  content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);root.addView(content);
  if(screen==0)chat();else if(screen==1)tasks();else device();
 }
 private String request(String path,String method,JSONObject body)throws Exception{
  HttpsURLConnection connection=open(path,method,body);try(InputStream stream=connection.getInputStream()){ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buffer=new byte[4096];int n;while((n=stream.read(buffer))!=-1){if(bytes.size()+n>2000000)throw new Exception("Phản hồi quá lớn.");bytes.write(buffer,0,n);}return bytes.toString("UTF-8");}finally{connection.disconnect();}
 }
 private HttpsURLConnection open(String path,String method,JSONObject body)throws Exception{
  HttpsURLConnection c=(HttpsURLConnection)new URI(server+path).toURL().openConnection();c.setInstanceFollowRedirects(false);c.setRequestMethod(method);c.setConnectTimeout(15000);c.setReadTimeout(180000);c.setRequestProperty("Content-Type","application/json");if(!token.isEmpty())c.setRequestProperty("Authorization","Bearer "+token);
  if(body!=null){c.setDoOutput(true);try(OutputStream out=c.getOutputStream()){out.write(body.toString().getBytes(StandardCharsets.UTF_8));}}
  if(c.getResponseCode()<200||c.getResponseCode()>=300){int status=c.getResponseCode();c.disconnect();throw new Exception("Yêu cầu không hoàn tất ("+status+"). Kiểm tra quyền thiết bị và nguồn AI.");}return c;
 }
 private void chat(){
  content.addView(text("AI Studio · phản hồi văn bản. Biểu đồ và biểu mẫu đầy đủ có trên web.",16));EditText prompt=input("Nhập yêu cầu",false);prompt.setSingleLine(false);content.addView(prompt);TextView output=text("",17);output.setTextIsSelectable(true);
  button(content,"Gửi",()->{String message=prompt.getText().toString().trim();if(message.isEmpty()||active!=null)return;stopped=false;output.setText("");run(()->{JSONObject body=new JSONObject().put("message",message).put("conversation","default").put("model","solo-default").put("ui_prompt","Use only root = Text(\"answer\") with a JSON quoted string. Available component Text(content).");HttpsURLConnection c=open("/api/chat","POST",body);active=c;StringBuilder result=new StringBuilder();boolean done=false;try(BufferedReader lines=new BufferedReader(new InputStreamReader(c.getInputStream(),StandardCharsets.UTF_8))){String line;while(!stopped&&(line=lines.readLine())!=null){if(!line.startsWith("data: "))continue;JSONObject event=new JSONObject(line.substring(6));String type=event.optString("type");if(type.equals("token")){result.append(event.optString("text"));String value=result.toString();ui(()->output.setText(readable(value)));}if(type.equals("error"))throw new Exception(event.optString("message","AI chưa hoàn tất."));if(type.equals("done")){done=true;break;}}}finally{active=null;c.disconnect();}boolean complete=done;ui(()->status.setText(complete?"Đã hoàn tất.":"Luồng đã dừng trước khi hoàn tất."));});});button(content,"Dừng",this::stop);content.addView(output);
 }
 private String readable(String source){try{int start=source.indexOf("Text(");if(start<0)return "Đang nhận nội dung…";String value=source.substring(start+5).trim();return (String)new JSONTokener(value).nextValue();}catch(Exception e){return "Đang nhận nội dung…";}}
 private void tasks(){
  EditText title=input("Công việc mới",false);content.addView(title);button(content,"Thêm",()->{String value=title.getText().toString().trim();if(value.isEmpty())return;run(()->{request("/api/tasks","POST",new JSONObject().put("title",value));ui(this::show);});});
  run(()->{JSONArray values=new JSONArray(request("/api/tasks","GET",null));ui(()->{status.setText("");for(int i=0;i<values.length();i++){JSONObject task=values.optJSONObject(i);if(task!=null)content.addView(text(task.optString("title")+" · "+task.optString("state"),17));}});});
 }
 private void device(){content.addView(text(server,17));content.addView(text("Quyền và thời hạn được quản lý trên web. Thu hồi thiết bị sẽ vô hiệu hóa đăng nhập này.",16));button(content,"Ngắt thiết bị",()->run(()->{String result="";try{request("/api/devices/self","DELETE",null);}catch(Exception e){result="Đã xóa đăng nhập trên máy. Hãy kiểm tra thu hồi thiết bị trên web.";}vault.clear();token="";String notice=result;ui(()->{show();status.setText(notice);});}));}
 private void stop(){stopped=true;HttpsURLConnection c=active;if(c!=null)c.disconnect();}
 @Override protected void onDestroy(){stop();executor.shutdownNow();super.onDestroy();}
}
