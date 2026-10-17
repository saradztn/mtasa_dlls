"""Deterministic industrial albedo/normal/roughness/AO generation + GTA DXT TXD."""
from pathlib import Path
import sys, math, io
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor/DragonFF'))
from gtaLib import txd
OUT=ROOT/'resource'/'textures'; SOURCE=ROOT/'tools'/'material_generator'/'generated'
N=256; rng=np.random.default_rng(23017)

def texture(name,color,rough=.65,kind='metal',alpha=255):
    yy,xx=np.mgrid[0:N,0:N]; noise=rng.normal(0,1,(N,N))*3.2
    base=np.zeros((N,N,4),np.uint8)
    for k,c in enumerate(color):base[:,:,k]=np.clip(c+noise,0,255)
    base[:,:,3]=alpha
    im=Image.fromarray(base,'RGBA'); d=ImageDraw.Draw(im)
    if kind=='metal':
      # rolled plate seams, fine directional scratches, and understated rivets
      for y in (0,127,255):d.line((0,y,N,y),fill=(8,12,17,255),width=2)
      for x in (0,127,255):d.line((x,0,x,N),fill=(78,90,100,210),width=1)
      for y in range(9,256,32):
       for x in range(9,256,32):
        d.ellipse((x-2,y-2,x+2,y+2),fill=(94,111,121,255),outline=(18,23,28,255))
      for k in range(240):
       x=int(rng.integers(0,N));y=int(rng.integers(0,N));l=int(rng.integers(5,45));d.line((x,y,min(255,x+l),y),fill=(80,94,102,45),width=1)
    elif kind=='grate':
      for x in range(0,N,16):d.line((x,0,x,N),fill=(16,21,27,255),width=3);d.line((x+2,0,x+2,N),fill=(77,90,99,210),width=1)
      for y in range(0,N,16):d.line((0,y,N,y),fill=(15,20,25,255),width=3)
      for x in range(7,N,16):
       for y in range(7,N,16):d.rectangle((x,y,x+3,y+3),fill=(5,8,11,255))
    elif kind=='concrete':
      for y in range(0,N,64):d.line((0,y,N,y),fill=(25,30,35,140),width=2)
      for k in range(150):
       x=int(rng.integers(N));y=int(rng.integers(N));r=int(rng.integers(1,4));v=int(rng.integers(-15,16));d.ellipse((x-r,y-r,x+r,y+r),fill=tuple(max(0,min(255,c+v)) for c in color)+(255,))
    elif kind=='glass':
      for x in range(0,N,128):d.line((x,0,x,N),fill=(122,178,196,100),width=2)
      for y in range(0,N,128):d.line((0,y,N,y),fill=(122,178,196,100),width=2)
      d.line((20,22,132,4),fill=(212,234,241,95),width=2)
    elif kind=='fabric':
      for k in range(0,N,4):d.line((k,0,k,N),fill=(color[0]+10,color[1]+8,color[2]+8,100),width=1)
      for k in range(0,N,4):d.line((0,k,N,k),fill=(10,10,12,50),width=1)
    elif kind=='warning':
      for k in range(-N,N*2,32):d.polygon([(k,0),(k+14,0),(k-N+14,N),(k-N,N)],fill=(235,171,48,255))
    elif kind=='rope':
      for k in range(0,N,7):d.line((k,0,k+35,N),fill=(199,169,117,255),width=2)
      for k in range(4,N,7):d.line((k,0,k+35,N),fill=(88,69,48,180),width=1)
    rgb=np.asarray(im.convert('RGB'),dtype=np.float32)
    # Tangent-space normal from seamless height field; subtle, fine-scale relief only.
    h=rgb.mean(2);dx=np.roll(h,-1,1)-np.roll(h,1,1);dy=np.roll(h,-1,0)-np.roll(h,1,0)
    nn=np.stack([-dx*0.65,-dy*0.65,np.full_like(dx,255)],2);nn=nn/np.maximum(np.linalg.norm(nn,axis=2,keepdims=True),1)*127.5+127.5
    # roughness is a grayscale map with material-specific microvariation
    rr=np.clip(rough*255+rng.normal(0,4,(N,N)),0,255).astype(np.uint8)
    # AO edge mask for tile seams and fastener depressions, restrained enough not to bake black lines.
    edge=np.minimum.reduce([xx,yy,N-1-xx,N-1-yy]);ao=np.clip(226+np.minimum(edge,8)*3+rng.normal(0,2,(N,N)),0,255).astype(np.uint8)
    return im,Image.fromarray(np.uint8(np.clip(nn,0,255)),'RGB'),Image.fromarray(rr,'L'),Image.fromarray(ao,'L')

MATS={
 'sq_floor':((24,31,39),.19,'grate',255), 'sq_steel':((39,49,59),.48,'metal',255),
 'sq_steel2':((73,84,91),.31,'metal',255),'sq_concrete':((56,62,68),.87,'concrete',255),
 'sq_glass':((93,142,158),.11,'glass',145),'sq_banner':((40,18,36),.78,'fabric',255),
 'sq_cyan':((17,211,242),.12,'metal',255),'sq_magenta':((238,31,139),.13,'metal',255),
 'sq_warning':((220,159,46),.56,'warning',255),'sq_rope':((144,112,72),.92,'rope',255)
}
def dds(im,fmt):
    bio=io.BytesIO(); im.save(bio,format='DDS',pixel_format=fmt); raw=bio.getvalue()
    if raw[:4]!=b'DDS ':raise RuntimeError('Pillow DDS writer did not generate DXT')
    return raw[128:]
def mipchain(im,alpha):
    out=[];cur=im
    while True:
      out.append(dds(cur,'DXT5' if alpha else 'DXT1'))
      if cur.width==1 and cur.height==1:break
      cur=cur.resize((max(1,cur.width//2),max(1,cur.height//2)),Image.Resampling.LANCZOS)
    return out
def native(name,im,alpha):
    t=txd.TextureNative();t.platform_id=9;t.filter_mode=6;t.uv_addressing=0x11;t.name=name;t.mask='';t.width=im.width;t.height=im.height;t.depth=32 if alpha else 16;t.raster_type=4
    t.raster_format_flags=(0x0500 if alpha else 0x0200)|0x8000;t.d3d_format=txd.D3DFormat.D3D_DXT5 if alpha else txd.D3DFormat.D3D_DXT1
    from collections import namedtuple
    PP=namedtuple('PlatformProperties','alpha cube_texture auto_mipmaps compressed');t.platform_properties=PP(alpha,False,False,True)
    t.pixels=mipchain(im,alpha);t.num_levels=len(t.pixels);return t

def build():
    SOURCE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True);textures=[]
    for name,(color,rough,kind,alpha) in MATS.items():
      base,norm,roughmap,ao=texture(name,color,rough,kind,alpha)
      base.save(SOURCE/(name+'_albedo.png'));norm.save(SOURCE/(name+'_normal.png'));roughmap.save(SOURCE/(name+'_roughness.png'));ao.save(SOURCE/(name+'_ao.png'))
      textures.append(native(name,base,alpha<255))
    d=txd.txd();d.device_id=txd.DeviceType.DEVICE_D3D9;d.native_textures=textures
    p=OUT/'squid_arena.txd';d.write_file(str(p),0x36003)
    print('TXD:',len(textures),'materials; PNG albedo/normal/roughness/AO maps generated')
if __name__=='__main__':build()
