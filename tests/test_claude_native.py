import sys
from pathlib import Path

import pytest

from server.engines import claude_native


@pytest.mark.asyncio
async def test_native_command_isolated_without_handling_credentials(tmp_path, monkeypatch):
    binary = tmp_path / "claude"
    binary.write_text(f"""#!{Path(sys.executable).resolve()}
import sys,json,os
assert 'BDSG_OWNER_TOKEN' not in os.environ
if sys.argv[1:]==['auth','status']:
 print(json.dumps({{'loggedIn':True,'authMethod':'claude.ai','secret':'never return'}}))
else:
 assert '--safe-mode' in sys.argv and '--bare' not in sys.argv
 assert sys.argv[sys.argv.index('--tools')+1]==''
 assert sys.argv[sys.argv.index('--disallowedTools')+1]=='*'
 assert '--dangerously-skip-permissions' not in sys.argv
 assert sys.stdin.read()=='request'
 print(json.dumps({{'type':'stream_event','event':{{'type':'content_block_delta','delta':{{'type':'text_delta','text':'hello'}}}}}}))
 print(json.dumps({{'type':'result','subtype':'success','is_error':False}}))
""")
    binary.chmod(0o700)
    monkeypatch.setenv("BDSG_CLAUDE_BINARY", str(binary))
    monkeypatch.setenv("BDSG_CLAUDE_HOME", str(tmp_path / "isolated"))
    monkeypatch.setenv("BDSG_OWNER_TOKEN", "secret")
    assert await claude_native.status() == {
        "installed": True,
        "connected": True,
        "auth_method": "claude.ai",
    }
    assert "".join([v async for v in claude_native.stream_text("request")]) == "hello"
