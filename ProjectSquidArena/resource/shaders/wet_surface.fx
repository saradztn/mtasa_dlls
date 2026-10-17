// MTA DX9 ps_3_0 wet metal/concrete approximation. SSR samples the captured scene; this is not ray tracing.
float4x4 gWorld : WORLD;
float4x4 gWorldViewProjection : WORLDVIEWPROJECTION;
float4x4 gViewProjection : VIEWPROJECTION;
float3 gCameraPosition : CAMERAPOSITION;
float gTime : TIME;
float gWetness=0.85;
float gReflect=0.46;
float gQuality=1.0;
texture gTexture0 < string textureState="0,Texture"; >;
texture gScreen;
sampler S0=sampler_state { Texture=(gTexture0); MinFilter=Anisotropic; MagFilter=Linear; MipFilter=Linear; };
sampler SS=sampler_state { Texture=(gScreen); MinFilter=Linear; MagFilter=Linear; MipFilter=None; AddressU=Clamp; AddressV=Clamp; };
struct VI { float3 Pos:POSITION0; float3 Normal:NORMAL0; float4 Color:COLOR0; float2 UV:TEXCOORD0; };
struct VO { float4 Pos:POSITION0; float4 Color:COLOR0; float2 UV:TEXCOORD0; float3 WP:TEXCOORD1; float3 N:TEXCOORD2; float4 Clip:TEXCOORD3; };
VO VS(VI i){VO o=(VO)0;o.Pos=mul(float4(i.Pos,1),gWorldViewProjection);o.Clip=o.Pos;o.WP=mul(float4(i.Pos,1),gWorld).xyz;o.N=normalize(mul(i.Normal,(float3x3)gWorld));o.UV=i.UV;o.Color=i.Color;return o;}
float hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float4 PS(VO i):COLOR0{
 float4 base=tex2D(S0,i.UV)*i.Color;
 float3 N=normalize(i.N);float3 V=normalize(gCameraPosition-i.WP);
 float2 p=i.WP.xy*0.75;float n=hash(floor(p))+hash(floor(p*3.7))*0.25;
 float wet=saturate(gWetness*(0.56+0.44*saturate(n)));
 float3 R=reflect(-V,N);float3 far=i.WP+R*35.0;float4 cp=mul(float4(far,1),gViewProjection);
 float2 uv=cp.xy/max(cp.w,0.001)*float2(0.5,-0.5)+0.5;
 float edge=saturate(min(min(uv.x,uv.y),min(1-uv.x,1-uv.y))*12);
 float valid=edge*step(0.01,cp.w)*saturate(1-length(i.WP-gCameraPosition)/130);
 float2 jitter=float2(sin(i.WP.x*1.8+gTime*.5),cos(i.WP.y*2.1-gTime*.3))*0.0012*(1-wet);
 float3 reflection=tex2D(SS,uv+jitter).rgb;
 float fres=pow(1-saturate(dot(N,V)),4);
 float refl=valid*gReflect*wet*saturate(0.18+fres*1.2);
 float3 cool=float3(0.025,0.075,0.105)*(0.3+fres);
 float3 result=base.rgb*(1-wet*0.24)+lerp(cool,reflection,valid)*refl;
 float spec=pow(saturate(dot(reflect(-V,N),normalize(float3(-.35,.6,.72)))),48)*wet*0.25;
 result+=float3(.2,.65,.8)*spec;
 return float4(result,base.a);
}
technique WetReflect { pass P0 { VertexShader=compile vs_3_0 VS(); PixelShader=compile ps_3_0 PS(); } }
technique Fallback { pass P0 { } }
