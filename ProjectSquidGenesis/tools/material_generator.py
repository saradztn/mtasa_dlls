"""Deterministic periodic materials. RGB normals + packed roughness/AO/wet-mask/metal."""
from pathlib import Path
import argparse, json, io, sys
from collections import namedtuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter
sys.path.insert(0,str(Path(__file__).parent/'vendor/DragonFF'))
from gtaLib import txd
ROOT=Path(__file__).resolve().parents[1]
PALETTE={'concrete':([72,79,86],.87,0),'industrial':([53,59,65],.9,0),'floor':([48,55,61],.55,.65),'steel':([38,45,52],.62,.85),'frame':([68,77,82],.32,.9),'rope':([151,119,75],.95,0),'glass':([114,174,182],.12,0),'asphalt':([36,40,46],.93,0),'warning':([163,128,39],.62,.3),'rubber':([28,31,33],.98,0),'door':([51,64,73],.49,.6),'bolt':([101,109,113],.25,.95),'cyan':([20,188,220],.4,0),'pink':([219,24,119],.4,0),'amber':([231,169,77],.4,0),'signage':([22,29,36],.6,.25)}
def generate(name,color,rough,metal,n=1024,seed=42,detail=1,scale=1,contrast=1,wet=.65,normal=1,out=None):
    rng=np.random.default_rng(seed); y,x=np.mgrid[:n,:n]/n
    broad=gaussian_filter(rng.normal(size=(n,n)),max(1,n/45*scale),mode='wrap'); broad/=max(broad.std(),1e-6)
    fine=rng.normal(size=(n,n)); h=.45*broad+.16*fine
    if name=='rope': h+=.8*np.sin(2*np.pi*(24*x+6*y))+.25*np.sin(2*np.pi*(96*x+24*y))
    if name=='floor': h+=((np.sin(2*np.pi*20*(x+y))>.9)|(np.sin(2*np.pi*20*(x-y))>.9))*.9
    if name in ('steel','frame','door','bolt'): h=gaussian_filter(h,(.5,5),mode='wrap')+.12*np.sin(2*np.pi*180*y)
    base=np.clip(np.array(color)[None,None,:]*(1+h[:,:,None]*.12*detail*contrast),0,255)
    if name=='warning': base[((x+y)*8%1)<.45]=[30,33,36]
    if name in ('cyan','pink','amber'): base[:]=color; h*=.03
    if name=='signage': h[:]=0
    a=np.full((n,n,1),104 if name=='glass' else 255)
    albedo=Image.fromarray(np.concatenate((base,a),2).astype('uint8'),'RGBA')
    if name=='signage':
        draw=ImageDraw.Draw(albedo);font=ImageFont.load_default(size=max(10,int(n*.063)))
        labels=['01 / TUG OF WAR','02 / GLASS BRIDGE','GENESIS / ENTRY','SERVICE / ACCESS']
        for row,(label,accent) in enumerate(zip(labels,[(32,190,218),(213,36,120),(225,170,84),(140,160,176)])):
            top=row*n//4;draw.rectangle((n*.03,top+n*.04,n*.05,top+n*.21),fill=accent)
            draw.text((n*.08,top+n*.08),label,font=font,fill=accent)
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*normal*.35; dy=(np.roll(h,-1,0)-np.roll(h,1,0))*normal*.35
    norms=np.stack((-dx,-dy,np.ones_like(h)),2); norms/=np.linalg.norm(norms,axis=2,keepdims=True)
    norm=Image.fromarray(np.uint8(np.clip(norms*.5+.5,0,1)*255))
    surf=np.stack((np.clip(rough+h*.04,.05,1),np.clip(.93+h*.025,.65,1),np.clip(wet*.5+broad*.12,0,1),np.full_like(h,metal)),2)
    packed=Image.fromarray(np.uint8(surf*255),'RGBA')
    if out:
        out=Path(out); out.mkdir(parents=True,exist_ok=True)
        albedo.save(out/f'{name}_base.png'); norm.save(out/f'{name}_normal.png'); packed.save(out/f'{name}_surface.png')
    return albedo,norm,packed

def native(name,image):
    t=txd.TextureNative(); t.platform_id=9;t.filter_mode=6;t.uv_addressing=0x11;t.name='psg_'+name;t.mask='';t.width=image.width;t.height=image.height;t.depth=32;t.raster_type=4;t.raster_format_flags=0x8500;t.d3d_format=txd.D3DFormat.D3D_DXT5
    P=namedtuple('PlatformProperties','alpha cube_texture auto_mipmaps compressed');t.platform_properties=P(name=='glass',False,False,True);t.pixels=[]
    while True:
        b=io.BytesIO();image.save(b,format='DDS',pixel_format='DXT5');assert b.getvalue()[:4]==b'DDS ';t.pixels.append(b.getvalue()[128:])
        if image.width==1:break
        image=image.resize((max(1,image.width//2),max(1,image.height//2)),Image.Resampling.LANCZOS)
    t.num_levels=len(t.pixels);return t

def build():
    images={}; settings={}
    for i,(name,(color,rough,metal)) in enumerate(PALETTE.items()):
        n=256 if name in ('cyan','pink','amber','bolt','rubber') else 1024
        maps=generate(name,color,rough,metal,n,42+i,out=ROOT/'source_assets/materials')
        images[name]=maps[0];settings[name]={'color':color,'roughness':rough,'metallic':metal,'resolution':n,'seed':42+i}
        for tier,size in [('low',256),('medium',512),('high',1024)]:
            dest=ROOT/'textures'/tier;dest.mkdir(parents=True,exist_ok=True)
            for label,img in zip(('normal','surface'),maps[1:]):img.resize((min(size,n),)*2).save(dest/f'{name}_{label}.png')
    for tier,size in [('low',256),('medium',512),('high',1024)]:
        d=txd.txd();d.device_id=txd.DeviceType.DEVICE_D3D9;d.native_textures=[native(k,v.resize((min(size,v.width),)*2)) for k,v in images.items()];d.write_file(str(ROOT/f'textures/{tier}/genesis.txd'),0x36003)
    (ROOT/'source_assets/materials/settings.json').write_text(json.dumps(settings,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--all',action='store_true');p.add_argument('--name',default='concrete',choices=PALETTE);p.add_argument('--color',nargs=3,type=int);p.add_argument('--roughness',type=float);p.add_argument('--detail',type=float,default=1);p.add_argument('--scale',type=float,default=1);p.add_argument('--contrast',type=float,default=1);p.add_argument('--wetness',type=float,default=.65);p.add_argument('--normal',type=float,default=1);p.add_argument('--resolution',type=int,choices=[128,256,512,1024,2048],default=1024);p.add_argument('--seed',type=int,default=42);p.add_argument('--output',default=str(ROOT/'source_assets/materials'));a=p.parse_args()
    if a.all:build()
    else:
        c,r,m=PALETTE[a.name];generate(a.name,a.color or c,r if a.roughness is None else a.roughness,m,a.resolution,a.seed,a.detail,a.scale,a.contrast,a.wetness,a.normal,a.output)
