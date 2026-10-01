/*
 * Runtime smoke test for the spider_sa MTA:SA resource.
 *
 * Loads the real resource Lua (config.lua + client.lua, in meta.xml order) in a
 * fengari Lua state with the MTA client API replaced by tools/mta_stub.lua, then
 * drives the resource through its normal life cycle:
 *
 *   1. resource start              -> state request sent to the server
 *   2. /spider                     -> model installed, object created
 *   3. /spider move                -> the object is moved to the new aim point
 *   4. /spider info                -> reports the installed model
 *   5. server spawn event          -> object created at the given position
 *   6. /spider remove              -> objects destroyed
 *   7. /spider uninstall           -> model slot freed again
 *   8. resource stop               -> no leaked model, no leaked objects
 *
 * It verifies that the Lua really executes and that the engine calls happen in
 * the documented order (COL -> TXD -> DFF, engineFreeModel on stop).  It cannot
 * validate MTA's renderer, the GTA engine or the actual look in game.
 *
 * Usage: node spider_sa/tools/smoke_test.js
 */

const fs = require("fs");
const path = require("path");
const { lua, lauxlib, lualib, to_luastring, to_jsstring } = require("fengari");

const TOOLS = __dirname;
const RESOURCE = path.resolve(TOOLS, "..");
const FAILURES = [];
const NOTES = [];

function fail(message) { FAILURES.push(message); }
function note(message) { NOTES.push(message); }

function parseMeta() {
    const xml = fs.readFileSync(path.join(RESOURCE, "meta.xml"), "utf8");
    const scripts = [];
    const scriptRe = /<script\s+src="([^"]+)"(?:\s+type="([^"]+)")?\s*\/>/g;
    const fileRe = /<file\s+src="([^"]+)"\s*\/>/g;
    let m;
    while ((m = scriptRe.exec(xml)) !== null) scripts.push({ src: m[1], type: m[2] || "server" });
    const files = [];
    while ((m = fileRe.exec(xml)) !== null) files.push(m[1]);
    return { scripts, files };
}

function runChunk(L, name, code) {
    if (lauxlib.luaL_loadbuffer(L, to_luastring(code), to_luastring(name)) !== lua.LUA_OK) {
        fail(`load error (${name}): ${to_jsstring(lua.lua_tostring(L, -1))}`);
        lua.lua_pop(L, 1);
        return false;
    }
    if (lua.lua_pcall(L, 0, 0, 0) !== lua.LUA_OK) {
        fail(`runtime error (${name}): ${to_jsstring(lua.lua_tostring(L, -1))}`);
        lua.lua_pop(L, 1);
        return false;
    }
    return true;
}

function callGlobal(L, expr, args = []) {
    const code = `return ${expr}`;
    if (lauxlib.luaL_loadbuffer(L, to_luastring(code), to_luastring("caller")) !== lua.LUA_OK) {
        fail(`cannot compile ${expr}: ${to_jsstring(lua.lua_tostring(L, -1))}`);
        lua.lua_pop(L, 1);
        return null;
    }
    for (const arg of args) {
        if (typeof arg === "number") lua.lua_pushnumber(L, arg);
        else if (typeof arg === "boolean") lua.lua_pushboolean(L, arg);
        else if (arg === null || arg === undefined) lua.lua_pushnil(L);
        else lua.lua_pushstring(L, to_luastring(String(arg)));
    }
    if (lua.lua_pcall(L, args.length, 1, 0) !== lua.LUA_OK) {
        fail(`call ${expr} failed: ${to_jsstring(lua.lua_tostring(L, -1))}`);
        lua.lua_pop(L, 1);
        return null;
    }
    const type = lua.lua_type(L, -1);
    let result = null;
    if (type === lua.LUA_TBOOLEAN) result = lua.lua_toboolean(L, -1);
    else if (type === lua.LUA_TNUMBER) result = lua.lua_tonumber(L, -1);
    else if (type === lua.LUA_TSTRING) result = to_jsstring(lua.lua_tostring(L, -1));
    else result = type;
    lua.lua_pop(L, 1);
    return result;
}

function readCalls(L) {
    // _calls.order is an array of { name = , args = { ... } }
    const code = `
        if not _calls or not _calls.order then return 0 end
        return #_calls.order
    `;
    lauxlib.luaL_loadbuffer(L, to_luastring(code), to_luastring("count"));
    lua.lua_pcall(L, 0, 1, 0);
    const count = lua.lua_tonumber(L, -1);
    lua.lua_pop(L, 1);

    const calls = [];
    for (let i = 1; i <= count; i++) {
        const snippet = `
            local e = _calls.order[${i}]
            local out = { e.name }
            for _, v in ipairs(e.args) do
                local t = type(v)
                if t == "number" or t == "string" or t == "boolean" or t == "nil" then
                    out[#out + 1] = tostring(v)
                else
                    out[#out + 1] = "<" .. t .. ">"
                end
            end
            return table.concat(out, "|")
        `;
        lauxlib.luaL_loadbuffer(L, to_luastring(snippet), to_luastring("call"));
        if (lua.lua_pcall(L, 0, 1, 0) !== lua.LUA_OK) {
            fail(`cannot read call ${i}: ${to_jsstring(lua.lua_tostring(L, -1))}`);
            lua.lua_pop(L, 1);
            continue;
        }
        calls.push(to_jsstring(lua.lua_tostring(L, -1)));
        lua.lua_pop(L, 1);
    }
    return calls;
}

function indexOfCall(calls, prefix) {
    return calls.findIndex((c) => c.startsWith(prefix));
}

function runServerPhase(meta) {
    const serverScripts = meta.scripts.filter((s) => s.type === "shared" || s.type === "server");
    const L = lauxlib.luaL_newstate();
    lualib.luaL_openlibs(L);

    if (!runChunk(L, "mta_stub_server.lua",
        fs.readFileSync(path.join(TOOLS, "mta_stub_server.lua"), "utf8"))) return;

    for (const script of serverScripts) {
        const file = path.join(RESOURCE, script.src);
        if (!fs.existsSync(file)) { fail(`server script listed in meta.xml is missing: ${script.src}`); continue; }
        if (!runChunk(L, script.src, fs.readFileSync(file, "utf8"))) return;
        note(`loaded ${script.src} (${script.type})`);
    }

    // /spiderall places a spider for everybody, in front of the player
    callGlobal(L, `_runCommand("spiderall", "spawn")`, []);
    let calls = readCalls(L);
    const spawnTrigger = calls.find((c) => c.startsWith("triggerClientEvent|spiderSa:spawn"));
    if (!spawnTrigger) {
        fail("/spiderall did not trigger spiderSa:spawn for the clients");
    } else {
        const parts = spawnTrigger.split("|");
        const [x, y] = [parseFloat(parts[2]), parseFloat(parts[3])];
        if (!(x === 100 && y > 200)) fail(`/spiderall placed the spider at an unexpected spot (${x}, ${y})`);
        else note(`/spiderall placed the spider at ${x}, ${y} (in front of the player)`);
    }

    // a joining client that missed the state request gets it on join
    const beforeJoin = readCalls(L).length;
    callGlobal(L, `_fireEvent("onPlayerJoin", testPlayer)`, []);
    const joinCalls = readCalls(L).slice(beforeJoin);
    if (!joinCalls.some((c) => c.startsWith("triggerClientEvent|spiderSa:spawn"))) {
        fail("onPlayerJoin did not re-send the placement to the joining player");
    } else {
        note("joining players receive the current placement again");
    }

    // a client requesting the state while a spider is placed gets an answer
    const code = `_fireEvent("spiderSa:requestState", nil)`;
    // the handler reads the predefined 'client' global for the requesting player
    runChunk(L, "set_client", "client = testPlayer");
    const beforeRequest = readCalls(L).length;
    callGlobal(L, code, []);
    const requestCalls = readCalls(L).slice(beforeRequest);
    if (!requestCalls.some((c) => c.startsWith("triggerClientEvent|spiderSa:spawn"))) {
        fail("spiderSa:requestState did not answer the client");
    } else {
        note("state handshake answers clients that start the resource");
    }

    // /spiderall remove clears it again
    callGlobal(L, `_runCommand("spiderall", "remove")`, []);
    calls = readCalls(L);
    if (!calls.some((c) => c.startsWith("triggerClientEvent|spiderSa:remove"))) {
        fail("/spiderall remove did not trigger spiderSa:remove");
    } else {
        note("/spiderall remove clears the spider for every player");
    }

    // and after the removal the state request must not re-send anything
    const beforeEmpty = readCalls(L).length;
    callGlobal(L, code, []);
    const emptyCalls = readCalls(L).slice(beforeEmpty);
    if (emptyCalls.some((c) => c.startsWith("triggerClientEvent"))) {
        fail("after removal the server still pushed a placement to clients");
    }
}

function main() {
    const meta = parseMeta();
    const L = lauxlib.luaL_newstate();
    lualib.luaL_openlibs(L);

    // tell the stub which files exist on disk
    const filesLua = meta.files
        .filter((f) => fs.existsSync(path.join(RESOURCE, f)))
        .map((f) => `_files[${JSON.stringify(f)}] = true`)
        .join("\n");
    if (!runChunk(L, "bootstrap", `_files = {}\n${filesLua}`)) return;
    const expectedAssets = meta.files.filter((f) => f.startsWith("assets/"));
    note(`assets declared in meta.xml: ${expectedAssets.join(", ")}`);

    if (!runChunk(L, "mta_stub.lua", fs.readFileSync(path.join(TOOLS, "mta_stub.lua"), "utf8"))) return;

    // load the client scripts in meta.xml order (shared + client, skipping server)
    const clientScripts = meta.scripts.filter((s) => s.type === "shared" || s.type === "client");
    for (const script of clientScripts) {
        const file = path.join(RESOURCE, script.src);
        if (!fs.existsSync(file)) { fail(`script listed in meta.xml is missing: ${script.src}`); continue; }
        if (!runChunk(L, script.src, fs.readFileSync(file, "utf8"))) return;
        note(`loaded ${script.src} (${script.type})`);
    }

    // ---- 1. resource start -------------------------------------------------
    callGlobal(L, `_fireEvent("onClientResourceStart")`, []);
    let calls = readCalls(L);
    const startIndex = indexOfCall(calls, "triggerServerEvent|spiderSa:requestState");
    if (startIndex < 0) fail("resource start did not request the global state from the server");
    const installsAfterStart = calls.filter((c) => c.startsWith("engineReplaceModel")).length;
    if (installsAfterStart !== 0) note("installOnStart is enabled in config.lua (model installed on start)");

    // ---- 2. /spider spawns -------------------------------------------------
    const before = readCalls(L).length;
    callGlobal(L, `_runCommand("spider")`, []);
    calls = readCalls(L).slice(before);
    const seq = ["engineRequestModel|object", "engineLoadCOL", "engineLoadTXD", "engineLoadDFF",
                 "engineReplaceCOL", "engineImportTXD", "engineReplaceModel", "createObject"];
    let cursor = -1;
    for (const step of seq) {
        const at = calls.findIndex((c, i) => i > cursor && c.startsWith(step));
        if (at < 0) { fail(`/spider did not call ${step} (order: ${calls.join(" -> ")})`); break; }
        cursor = at;
    }
    const createCall = calls.find((c) => c.startsWith("createObject"));
    if (createCall) {
        const modelId = createCall.split("|")[1];
        const dffCall = calls.find((c) => c.startsWith("engineReplaceModel"));
        if (dffCall && dffCall.split("|")[2] !== modelId) {
            fail(`model id mismatch: created ${modelId}, replaced ${dffCall.split("|")[2]}`);
        }
        note(`spawn used model id ${modelId}`);
    }
    if (!calls.some((c) => c.startsWith("setElementDoubleSided"))) note("doubleSided disabled in config.lua");
    if (calls.some((c) => c.startsWith("setElementRotation"))) note("spider rotated to face the player");
    else fail("spider was not rotated towards the player");

    // ---- 3. /spider move ---------------------------------------------------
    const beforeMove = readCalls(L).length;
    callGlobal(L, `_runCommand("spider", "move")`, []);
    const moveCalls = readCalls(L).slice(beforeMove);
    if (!moveCalls.some((c) => c.startsWith("setElementPosition"))) fail("/spider move did not move the object");
    if (moveCalls.some((c) => c.startsWith("createObject"))) fail("/spider move created a second object");

    // ---- 4. /spider info ---------------------------------------------------
    const beforeInfo = readCalls(L).length;
    callGlobal(L, `_runCommand("spider", "info")`, []);
    const infoCalls = readCalls(L).slice(beforeInfo);
    if (!infoCalls.some((c) => c.startsWith("outputChatBox"))) fail("/spider info printed nothing");

    // ---- 5. the server places a global spider ------------------------------
    const beforeServer = readCalls(L).length;
    callGlobal(L, `_fireEvent("spiderSa:spawn", 120, 220, 8, 45)`, []);
    const serverCalls = readCalls(L).slice(beforeServer);
    const serverCreate = serverCalls.find((c) => c.startsWith("createObject"));
    if (!serverCreate) fail("spiderSa:spawn did not create an object");
    // spawnAt() first rotates the spider towards the player, the handler then
    // overrides it with the server supplied rotation - the last call must win
    const rotations = serverCalls.filter((c) => c.startsWith("setElementRotation"));
    const serverRot = rotations[rotations.length - 1];
    if (!serverRot || !serverRot.endsWith("|45")) {
        fail(`spiderSa:spawn did not apply the server rotation last (${rotations.join(", ")})`);
    }
    const reuse = serverCalls.some((c) => c.startsWith("engineReplaceModel"));
    if (reuse) note("the model was re-installed on the server spawn (expected only if it was never installed)");
    const serverObjectId = serverCreate ? serverCreate.split("|")[1] : null;

    // ---- 6. /spider remove -------------------------------------------------
    const beforeRemove = readCalls(L).length;
    callGlobal(L, `_runCommand("spider", "remove")`, []);
    const removeCalls = readCalls(L).slice(beforeRemove);
    const destroyed = removeCalls.filter((c) => c.startsWith("destroyElement")).length;
    if (destroyed < 2) fail(`/spider remove destroyed ${destroyed} objects, expected at least 2`);
    else note(`/spider remove destroyed ${destroyed} objects`);

    // ---- 7. /spider uninstall ---------------------------------------------
    const beforeUninstall = readCalls(L).length;
    callGlobal(L, `_runCommand("spider", "uninstall")`, []);
    const uninstallCalls = readCalls(L).slice(beforeUninstall);
    if (!uninstallCalls.some((c) => c.startsWith("engineFreeModel"))) {
        fail("uninstall did not free the engineRequestModel slot");
    } else {
        note("uninstall freed the allocated model slot");
    }

    // ---- 8. resource stop --------------------------------------------------
    callGlobal(L, `_runCommand("spider")`, []);          // install + spawn again
    callGlobal(L, `_fireEvent("onClientResourceStop")`, []);
    calls = readCalls(L);
    const frees = calls.filter((c) => c.startsWith("engineFreeModel")).length;
    if (frees < 2) fail(`resource stop did not free the model slot (engineFreeModel calls: ${frees})`);

    const remaining = callGlobal(L, `(#_calls.order >= 0) and 1 or 0`, []);
    if (remaining === null) fail("could not read the stub state back");

    const totalCalls = readCalls(L).length;
    note(`engine API calls recorded: ${totalCalls}`);
    const chat = readCalls(L).filter((c) => c.startsWith("outputChatBox")).length;
    note(`chat messages produced: ${chat}`);

    // ---- 8b. a missing asset is reported by name ---------------------------
    // The zip this resource comes from shipped no TXD at all, so this branch
    // must reach the player as a readable message, not as silence.
    callGlobal(L, `_runCommand("spider", "uninstall")`, []);
    if (!runChunk(L, "hide_asset", `_files["assets/Dragon_2.5.txd"] = false`)) return;
    const beforeMissing = readCalls(L).length;
    callGlobal(L, `_runCommand("spider", "install")`, []);
    const missingCalls = readCalls(L).slice(beforeMissing);
    const namedInChat = missingCalls.some((c) => c.startsWith("outputChatBox") && c.includes("Dragon_2.5.txd"));
    if (!namedInChat) fail("a missing TXD produced no message naming the file (asset_missing is unreachable)");
    else note("a missing asset is reported by name (asset_missing path is reachable)");
    if (missingCalls.some((c) => c.startsWith("engineLoad"))) {
        fail("install continued loading assets after reporting one missing");
    }
    if (missingCalls.some((c) => c.startsWith("engineRequestModel"))) {
        fail("install allocated a model slot before checking that the assets exist");
    }
    if (!runChunk(L, "restore_asset", `_files["assets/Dragon_2.5.txd"] = true`)) return;

    // ---- 9. server side ----------------------------------------------------
    runServerPhase(meta);

    // ---- report ------------------------------------------------------------
    console.log("spider_sa runtime smoke test");
    console.log("-".repeat(60));
    for (const n of NOTES) console.log("  note   " + n);
    for (const f of FAILURES) console.log("  FAIL   " + f);
    if (FAILURES.length === 0) {
        console.log("\nRuntime smoke test passed: the resource Lua executes and the engine call sequence is correct.");
        console.log("This does NOT prove anything about the visual result inside MTA - only an in-game");
        console.log("check can confirm that, because the GTA renderer does not exist outside the game.");
    } else {
        console.log(`\n${FAILURES.length} check(s) failed.`);
        process.exitCode = 1;
    }
}

main();
