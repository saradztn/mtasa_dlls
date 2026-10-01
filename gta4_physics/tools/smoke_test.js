/*
 * Runtime smoke test for the gta4_physics MTA:SA resource.
 *
 * Loads every non-server Lua file in meta.xml order inside a fengari (Lua 5.3)
 * state with minimal MTA API stubs, then drives a simulated vehicle for twelve
 * seconds and checks the emulator's internal state. This verifies that the Lua
 * code really executes (no nil indexing, arithmetic on nil, bad comparisons)
 * and that the model produces plausible numbers. It cannot validate MTA's own
 * solver or GPU/engine behaviour, because those do not exist outside the game.
 *
 * Usage: node gta4_physics/tools/smoke_test.js
 */

const fs = require("fs");
const path = require("path");
const { lua, lauxlib, lualib, to_luastring, to_jsstring } = require("fengari");

const RESOURCE = path.resolve(__dirname, "..");
const FAILURES = [];

function parseMeta() {
    const xml = fs.readFileSync(path.join(RESOURCE, "meta.xml"), "utf8");
    const scripts = [];
    const re = /<script\s+src="([^"]+)"(?:\s+type="([^"]+)")?\s*\/>/g;
    let match;
    while ((match = re.exec(xml)) !== null) {
        scripts.push({ src: match[1], type: match[2] || "server" });
    }
    return scripts;
}

function runChunk(L, name, code) {
    if (lauxlib.luaL_loadbuffer(L, to_luastring(code), to_luastring(name)) !== lua.LUA_OK) {
        FAILURES.push(`load error (${name}): ${to_jsstring(lua.lua_tostring(L, -1))}`);
        lua.lua_pop(L, 1);
        return false;
    }
    if (lua.lua_pcall(L, 0, 0, 0) !== lua.LUA_OK) {
        FAILURES.push(`runtime error (${name}): ${to_jsstring(lua.lua_tostring(L, -1))}`);
        lua.lua_pop(L, 1);
        return false;
    }
    return true;
}

function readTable(L, name) {
    lua.lua_getglobal(L, to_luastring(name));
    if (!lua.lua_istable(L, -1)) {
        lua.lua_pop(L, 1);
        return null;
    }
    const index = lua.lua_gettop(L);
    const result = {};
    lua.lua_pushnil(L);
    while (lua.lua_next(L, index) !== 0) {
        const keyType = lua.lua_type(L, -2);
        let key = null;
        if (keyType === lua.LUA_TNUMBER) key = lua.lua_tonumber(L, -2);
        else if (keyType === lua.LUA_TSTRING) key = to_jsstring(lua.lua_tostring(L, -2));
        if (key !== null) {
            const type = lua.lua_type(L, -1);
            if (type === lua.LUA_TSTRING) result[key] = to_jsstring(lua.lua_tostring(L, -1));
            else if (type === lua.LUA_TNUMBER) result[key] = lua.lua_tonumber(L, -1);
            else if (type === lua.LUA_TBOOLEAN) result[key] = lua.lua_toboolean(L, -1);
        }
        lua.lua_pop(L, 1);
    }
    lua.lua_pop(L, 1);
    return result;
}

const BOOTSTRAP = `
    root = {}
    resourceRoot = {}
    localPlayer = {}
    source = nil
    client = nil
    local handlers = {}
    __G4_handlers = handlers
    function addEvent(name) handlers[name] = handlers[name] or {} end
    function addEventHandler(name, element, fn)
        handlers[name] = handlers[name] or {}
        table.insert(handlers[name], { element = element, fn = fn })
    end
    function removeEventHandler(name, element, fn)
        local list = handlers[name]
        if not list then return end
        for index = #list, 1, -1 do
            if fn == nil or list[index].fn == fn then table.remove(list, index) end
        end
    end
    function triggerEvent(name, element, ...)
        local list = handlers[name] or {}
        for _, entry in ipairs(list) do
            source = element
            entry.fn(...)
        end
    end
    function addCommandHandler() end
    function removeCommandHandler() end
`;

function main() {
    const L = lauxlib.luaL_newstate();
    lualib.luaL_openlibs(L);

    if (!runChunk(L, "bootstrap", BOOTSTRAP)) return report(L);

    for (const script of parseMeta()) {
        if (script.type === "server") continue;
        const code = fs.readFileSync(path.join(RESOURCE, script.src), "utf8");
        if (!runChunk(L, script.src, code)) return report(L);
    }
    if (!runChunk(L, "tools/mta_stub.lua", fs.readFileSync(path.join(__dirname, "mta_stub.lua"), "utf8"))) return report(L);
    if (!runChunk(L, "tools/smoke_assert.lua", fs.readFileSync(path.join(__dirname, "smoke_assert.lua"), "utf8"))) return report(L);

    return report(L);
}

function report(L) {
    const failures = readTable(L, "__G4_failures") || {};
    const summary = readTable(L, "__G4_report") || {};
    console.log("Scenario summary:");
    for (const key of Object.keys(summary).sort()) {
        const value = summary[key];
        console.log(`  ${String(key).padEnd(18)} ${typeof value === "number" ? value.toFixed(3) : value}`);
    }

    let count = 0;
    for (const key of Object.keys(failures).sort()) {
        count += 1;
        console.log(`  FAIL: ${failures[key]}`);
    }
    for (const line of FAILURES) {
        count += 1;
        console.log(`  FAIL: ${line}`);
    }
    if (count === 0) {
        console.log("\nRuntime smoke test passed");
        return;
    }
    console.log(`\n${count} failure(s)`);
    process.exitCode = 1;
}

main();
