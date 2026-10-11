package vn.bdsg.soloos;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

final class Vault {
 private static final String ALIAS="soloos.device";
 private final Context context;
 Vault(Context context){this.context=context;}
 private SecretKey key() throws Exception {
  KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);
  if(!store.containsAlias(ALIAS)){
   KeyGenerator generator=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
   generator.init(new KeyGenParameterSpec.Builder(ALIAS,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());generator.generateKey();
  }
  return (SecretKey)store.getKey(ALIAS,null);
 }
 void save(String server,String token) throws Exception {
  Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key());cipher.updateAAD(server.getBytes(java.nio.charset.StandardCharsets.UTF_8));
  String value=Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP)+":"+Base64.encodeToString(cipher.doFinal(token.getBytes(java.nio.charset.StandardCharsets.UTF_8)),Base64.NO_WRAP);
  if(!context.getSharedPreferences("device",0).edit().putString("server",server).putString("credential",value).commit())throw new Exception("Không lưu được thông tin thiết bị.");
 }
 String[] read() throws Exception {
  var prefs=context.getSharedPreferences("device",0);String server=prefs.getString("server",null),value=prefs.getString("credential",null);
  if(server==null||value==null)return null;
  String[] pieces=value.split(":");Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,Base64.decode(pieces[0],Base64.NO_WRAP)));cipher.updateAAD(server.getBytes(java.nio.charset.StandardCharsets.UTF_8));
  return new String[]{server,new String(cipher.doFinal(Base64.decode(pieces[1],Base64.NO_WRAP)),java.nio.charset.StandardCharsets.UTF_8)};
 }
 void clear(){context.getSharedPreferences("device",0).edit().clear().commit();}
}
