import hmac
import re

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from server.core.cms_render import layout
from server.core.i18n import static_html, t
from server.core.members import COOKIE, Members
from server.core.site import settings

router = APIRouter()


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def email_address(cls, v):
        v = v.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", v):
            raise ValueError("Invalid email")
        return v


class Register(Login):
    name: str = Field(min_length=1, max_length=100)


def guard(request):
    if request.headers.get("origin") not in request.app.state.settings.origins:
        raise HTTPException(403, t("Yêu cầu phải gửi từ website này."))
    ip = request.client.host if request.client else "unknown"
    if not request.app.state.store.rate_limit("members:" + ip, 10):
        raise HTTPException(429, t("Vui lòng thử lại sau một phút."))


@router.post("/api/members/register", status_code=201)
def register(body: Register, request: Request):
    guard(request)
    if not settings(request.app.state.cms).registration:
        raise HTTPException(403, t("Website chưa mở đăng ký."))
    Members(request.app.state.cms).register(body.email, body.name.strip(), body.password)
    return {"registered": True}


@router.post("/api/members/login")
def login(body: Login, request: Request, response: Response):
    guard(request)
    token = Members(request.app.state.cms).login(body.email, body.password)
    if not token:
        raise HTTPException(401, t("Email hoặc mật khẩu không đúng."))
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=request.app.state.settings.secure_cookies,
        samesite="strict",
        max_age=43200,
        path="/",
    )
    return {"authenticated": True}


@router.get("/api/members/session")
def session(request: Request):
    member = Members(request.app.state.cms).session(request.cookies.get(COOKIE, ""))
    if not member:
        raise HTTPException(401, t("Chưa đăng nhập."))
    return member


@router.delete("/api/members/session")
def logout(request: Request):
    member = session(request)
    if not hmac.compare_digest(member["csrf"], request.headers.get("x-csrf-token", "")):
        raise HTTPException(403, t("CSRF không hợp lệ."))
    Members(request.app.state.cms).logout(request.cookies.get(COOKIE, ""))
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/")
    return response


@router.get("/account", response_class=HTMLResponse)
def account(request: Request):
    site = settings(request.app.state.cms)
    registration = (
        static_html("""<details><summary>Đăng ký tài khoản</summary><form id="register"><label>Họ tên<input name="name" required maxlength="100" autocomplete="name"></label><label>Email<input name="email" type="email" required autocomplete="email"></label><label>Mật khẩu (từ 12 ký tự)<input name="password" type="password" required minlength="12" maxlength="128" autocomplete="new-password"></label><button>Đăng ký</button></form></details>""")
        if site.registration
        else ""
    )
    body = (
        static_html("""<h1>Tài khoản khách hàng</h1><p id="message" role="status"></p><section id="signed-in" hidden><p id="identity"></p><button id="logout">Đăng xuất</button></section><section id="signed-out"><form id="login"><label>Email<input name="email" type="email" required autocomplete="email"></label><label>Mật khẩu<input name="password" type="password" required minlength="12" maxlength="128" autocomplete="current-password"></label><button>Đăng nhập</button></form>""")
        + registration
        + static_html("""</section><p><a href="/admin">Đăng nhập quản trị viên</a></p><style>form{max-width:480px;margin:24px 0}label{display:block;margin:16px 0}input{display:block;width:100%;padding:14px;font:inherit;border:1px solid #aab8ac;border-radius:8px}button{padding:12px 24px;font:inherit;background:var(--accent);color:white;border:0;border-radius:8px;cursor:pointer}</style><script src="/member-client.js" defer></script>""")
    )
    return HTMLResponse(
        layout(t("Tài khoản · ") + site.title, body, site=site),
        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"},
    )


@router.get("/member-client.js")
def script():
    return Response(
        SCRIPT, media_type="application/javascript", headers={"Cache-Control": "no-store"}
    )


SCRIPT = r"""
const en=document.documentElement.lang==='en';
let csrf='';
const message=document.querySelector('#message');
async function call(path,method='GET',body){const response=await fetch('/api/members/'+path,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:body?JSON.stringify(body):undefined});if(!response.ok){const value=await response.json();throw Error(typeof value.detail==='string'?value.detail:(en?'Check the information you entered.':'Kiểm tra thông tin đã nhập.'))}return response.status===204?{}:response.json()}
async function refresh(){try{const user=await call('session');csrf=user.csrf;document.querySelector('#identity').textContent=user.name+' · '+user.email;document.querySelector('#signed-in').hidden=false;document.querySelector('#signed-out').hidden=true}catch(e){csrf='';document.querySelector('#signed-in').hidden=true;document.querySelector('#signed-out').hidden=false}}
for(const kind of ['login','register']){const form=document.getElementById(kind);if(form)form.addEventListener('submit',async e=>{e.preventDefault();const button=form.querySelector('button');button.disabled=true;message.textContent='';try{await call(kind,'POST',Object.fromEntries(new FormData(form)));form.reset();message.textContent=kind==='register'?(en?'Registered. You can now sign in.':'Đã đăng ký. Bạn có thể đăng nhập.'):'';await refresh()}catch(error){message.textContent=error.message}finally{button.disabled=false}})}
document.querySelector('#logout').onclick=async()=>{try{await call('session','DELETE');await refresh()}catch(error){message.textContent=error.message}};
refresh();
"""
