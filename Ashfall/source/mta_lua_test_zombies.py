# Created by: Arena.ai Agent Mode (AI) - runs the headless zombie AI scenario test (mta_zombie_test.lua) on the real resource files
import os, sys
from lupa import LuaRuntime
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'resource', 'Ashfall')
lua = LuaRuntime(unpack_returned_tuples=True)
fn = lua.eval('function(src, res) return load(src, "@mta_zombie_test.lua")(res) end')
fails = fn(open(os.path.join(HERE, 'mta_zombie_test.lua')).read(), RES)
sys.exit(1 if fails else 0)
