"""Offline file/parser tests, Lua 5.1 syntax and explicitly mocked lifecycle tests."""
from pathlib import Path
import sys,json,math,xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
from lupa.lua51 import LuaRuntime
sys.path.insert(0,str(Path(__file__).parent/'vendor/DragonFF'))
from gtaLib import dff,col,txd
ROOT=Path(__file__).resolve().parents[1];results=[]
def check(name,fn):
    try:detail=fn();results.append({'test':name,'status':'PASS','detail':detail})
    except Exception as e:results.append({'test':name,'status':'FAIL','detail':str(e)});raise
layout=json.loads((ROOT/'source_assets/layout.json').read_text())
def manifest():
    meta=ET.parse(ROOT/'meta.xml').getroot();paths=[e.get('src') for e in meta if e.get('src')];assert len(paths)==len(set(paths));assert all((ROOT/p).is_file() for p in paths)
    declared=set(paths)
    for folder in ['models','collisions','shaders','textures']:
        assert all(str(p.relative_to(ROOT)) in declared for p in (ROOT/folder).rglob('*') if p.is_file())
    assert not list(ROOT.rglob('*.blend1'));return len(paths)
check('XML and resource dependency closure',manifest)
def models():
    total=0
    for a in layout['assets']:
        d=dff.dff();d.load_file(str(ROOT/f'models/{a["name"]}.dff'));assert len(d.clumps)==1
        g=d.clumps[0].geometry_list[0];assert len(g.vertices)==a['vertices'];assert len(g.triangles)==a['triangles'];assert len(g.uv_layers[0])==len(g.vertices)
        xyz=np.array(g.vertices);assert np.isfinite(xyz).all();assert len(g.normals)==len(g.vertices)
        for n in g.normals:assert .98<sum(v*v for v in n)<1.02
        c=col.coll();c.load_file(str(ROOT/f'collisions/{a["name"]}.col'));assert len(c.models)==1
        assert len(c.models[0].boxes)==a['collision']['boxes'];total+=len(g.triangles)
    return {'models':len(layout['assets']),'unique_triangles':total}
check('DFF and COL parser roundtrip, UVs, finite unit normals',models)
def rope_lod():
    import gzip
    source=json.loads(gzip.open(ROOT/'source_assets/blender/mesh_sources.json.gz','rt').read())
    by_name={a['name']:a for a in layout['assets']};high=by_name['rope'];low=by_name['rope_low']
    assert low['role']=='lod_template' and low['triangles']==1920 and high['triangles']==17280
    assert not any(p['asset']=='rope_low' for p in layout['placements'])
    vertices=np.asarray(source['rope_low']['v']);t=(vertices[:,0]+20)/40
    from rope_profile import height
    center=np.array([height(x) for x in vertices[:,0]])
    radial=np.sqrt(vertices[:,1]**2+(vertices[:,2]-center)**2)
    assert np.all(radial<=.06601) and np.all(radial>=.04999)
    assert abs(vertices[:,0].min()+20)<1e-6 and abs(vertices[:,0].max()-20)<1e-6
    return {'near_triangles':high['triangles'],'distant_triangles':low['triangles'],'triangle_reduction_percent':100*(1-low['triangles']/high['triangles']),'same_authored_length_and_sag':True,'scope':'Authored geometry count, not measured FPS'}
check('Rope LOD geometry and matching centreline',rope_lod)

def textures():
    n=0
    for tier,limit in [('low',256),('medium',512),('high',1024)]:
        d=txd.txd();d.load_file(str(ROOT/f'textures/{tier}/genesis.txd'));assert len(d.native_textures)==len(json.loads((ROOT/'source_assets/materials/settings.json').read_text()))
        for t in d.native_textures:assert t.width<=limit;assert t.num_levels==int(math.log2(t.width))+1;assert t.name.startswith('psg_')
        for p in (ROOT/f'textures/{tier}').glob('*.png'):
            with Image.open(p) as im:im.verify()
            with Image.open(p) as im:assert im.size[0]==im.size[1]<=limit;n+=1
    return {'checked_map_images':n,'dictionaries':3}
check('Native TXD mip chains and map dimensions',textures)
def lua_syntax():
    vm=LuaRuntime(unpack_returned_tuples=True)
    for p in ROOT.rglob('*.lua'):
        vm.execute('assert(loadstring(...))',p.read_text())
    return 'All Lua scripts compiled with Lua 5.1 (not MTA execution)'
check('Lua 5.1 syntax',lua_syntax)
def walk():
    # Sample walkable surfaces on explicit authored entry paths. Not a capsule physics test.
    boxes=[b for a in layout['assets'] if a['role']=='structure' for b in _boxes(a)]
    routes=[r['points'] for r in json.loads((ROOT/'source_assets/interactions.json').read_text())['routes']]
    count=0
    for route in routes:
        for a,b in zip(route,route[1:]):
            for t in np.linspace(0,1,max(2,int(math.dist(a,b)*8))):
                x=a[0]*(1-t)+b[0]*t;y=a[1]*(1-t)+b[1]*t
                assert any(lo[0]-.001<=x<=hi[0]+.001 and lo[1]-.001<=y<=hi[1]+.001 and -.7<=hi[2]<=.05 for lo,hi in boxes),(x,y,'no floor')
                assert not any(lo[0]+.22<x<hi[0]-.22 and lo[1]+.22<y<hi[1]-.22 and lo[2]<1.7 and hi[2]>.3 for lo,hi in boxes),(x,y,'blocked')
                count+=1
    return {'floor_samples':count,'note':'Axis-aligned source collision boxes only. Full MTA capsule/streaming NOT TESTED.'}
def _boxes(a):
    c=col.coll();c.load_file(str(ROOT/f'collisions/{a["name"]}.col'));return [(list(b.min),list(b.max)) for b in c.models[0].boxes]
check('Entry-to-platform collision corridor samples',walk)
def grip_anchors():
    from rope_profile import height
    anchors=json.loads((ROOT/'source_assets/animations/grip_alignment.json').read_text())['anchors']
    assert len(anchors)==6
    for a in anchors:
        x=a['source_rig_root'][0]
        assert -19<x<-15 if a['team']=='left' else 15<x<19
        for p in a['palm_centres']:
            assert abs(p[1])<1e-8 and abs(p[2]-height(p[0]))<1e-8
            assert -20<=p[0]<=20 and abs(p[0])>14
    return 'Six source-rig anchors put both palm-centre proxies on the straight platform rope; GTA ped offsets/mesh contact NOT TESTED'
check('Tug source-rig anchor alignment',grip_anchors)
def interaction_zones():
    data=json.loads((ROOT/'source_assets/interactions.json').read_text());zones=data['zones']
    assert len(zones)==8 and len({z['id'] for z in zones})==8
    assert sum(z['kind']=='tug_slot' for z in zones)==6
    anchors={a['id']:a for a in json.loads((ROOT/'source_assets/animations/grip_alignment.json').read_text())['anchors']}
    boxes=[b for a in layout['assets'] if a['role']=='structure' for b in _boxes(a)]
    samples=0
    for zone in zones:
        assert all(math.isfinite(x) for x in zone['position'])
        assert 0<zone['radius']<=zone['exitRadius'] and zone['verticalTolerance']==1.5
        if zone['kind']=='tug_slot':assert zone['position']==anchors[zone['id']]['mta_spawn_reference']
        x,y,z=zone['position']
        for dx in [-.3,0,.3]:
            for dy in [-.3,0,.3]:
                xx=x+dx;yy=y+dy
                assert any(lo[0]<=xx<=hi[0] and lo[1]<=yy<=hi[1] and -.7<=hi[2]<=.05 for lo,hi in boxes),(zone['id'],'no floor')
                assert not any(lo[0]<xx<hi[0] and lo[1]<yy<hi[1] and lo[2]<1.7 and hi[2]>.3 for lo,hi in boxes),(zone['id'],'blocked')
                samples+=1
    return {'zones':len(zones),'canonical_centre_footprint_samples':samples,'scope':'Source collision boxes around canonical centres, not full approach radius or MTA capsule physics'}
check('Interaction station schema and nominal floor footprints',interaction_zones)


def server():
    vm=LuaRuntime(unpack_returned_tuples=True)
    vm.execute('''root={};resourceRoot={};commands={};events={};sent={};tick=10000
function addCommandHandler(n,f)commands[n]=f end
function addEvent()end
function addEventHandler(n,r,f)events[n]=f end
function isElement(e)return type(e)=='table' end
function getElementType(e)return e.kind end
function getTickCount()return tick end
function triggerClientEvent(...)table.insert(sent,{...})end
function hasObjectPermissionTo(p)return p.admin==true end
function outputChatBox()end
function isPedDead(p)return p.dead end
function isPedInVehicle(p)return p.vehicle end
function getElementPosition(p)return p.x,p.y,p.z end
function getElementRotation(p)return 0,0,p.rz end
function getElementDimension(p)return p.dimension end
function getElementInterior(p)return p.interior end
function setElementPosition(p,x,y,z)p.x=x;p.y=y;p.z=z end
function setElementRotation(p,x,y,z)p.rz=z end
function setElementDimension(p,d)p.dimension=d end
function setElementInterior(p,d)p.interior=d end
''')
    for p in ('shared/config.lua','server/main.lua','server/arena_state.lua'):vm.execute((ROOT/p).read_text())
    vm.execute('''
function event(name,p,...)source=resourceRoot;client=p;events[name](...)end
function ack(p)local last=sent[#sent];assert(last[2]=='psg:prepare');event('psg:prepared',p,last[5])end
function enter(p,place)commands.psg(p,'psg',place);ack(p)end
p={kind='player',x=10,y=20,z=30,rz=70,dimension=8,interior=2}
commands.psg(p,'psg','enter');assert(p.dimension==8 and #sent==0,'entry before load')
event('psg:loadStatus',p,'wrong',true);assert(not PSG_isClientReady(p))
source={};client=p;events['psg:loadStatus'](PSG_CONFIG.protocol,true);assert(not PSG_isClientReady(p),'spoofed source')
event('psg:loadStatus',p,PSG_CONFIG.protocol,true);assert(PSG_isClientReady(p))
commands.psg(p,'psg','enter');assert(p.dimension==8,'moved before acknowledgement')
event('psg:prepared',p,'forged');assert(p.dimension==8);ack(p);assert(p.dimension==2601 and p.y==4956)
enter(p,'tug');commands.psg(p,'psg','leave');assert(p.x==10 and p.y==20 and p.z==30 and p.rz==70 and p.dimension==8 and p.interior==2)
commands.psg(p,'psg','enter');local old=sent[#sent][5];commands.psg(p,'psg','glass');event('psg:prepared',p,old);assert(p.dimension==8);ack(p);assert(p.y==4977)
event('psg:loadStatus',p,PSG_CONFIG.protocol,false);assert(p.dimension==8 and not PSG_isClientReady(p),'load loss must restore')
event('psg:loadStatus',p,PSG_CONFIG.protocol,true)
commands.psg(p,'psg','enter');tick=tick+5001;ack(p);assert(p.dimension==8,'expired request')
commands.psg(p,'psg','enter');commands.psg(p,'psg','leave');ack(p);assert(p.dimension==8,'cancelled request')
commands.psg(p,'psg','enter');p.vehicle=true;ack(p);assert(p.dimension==8,'vehicle between request and ack');p.vehicle=false
assert(not setPanelState('invalid','broken'));assert(not setPanelState('GB_01_L','bad'))
local n=#sent;commands.psg_panel(p,'psg_panel','GB_01_L','broken');assert(#sent==n)
p.admin=true;commands.psg_panel(p,'psg_panel','GB_01_L','broken');assert(#sent==n+1)
assert(not events['psg:setPanelState']);event('psg:snapshot',p);local m=#sent;event('psg:snapshot',p);assert(#sent==m)
enter(p,'glass');events.onResourceStop();assert(p.dimension==8)
''');return 'Mocked ready gate, protocol/source rejection, request-token acknowledgement, stale/expired/cancelled requests, vehicle race, load-loss rollback, restoration, ACL panel states and throttled snapshot'
check('Server authority logic (mock APIs)',server)
(ROOT/'tests/offline_results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
