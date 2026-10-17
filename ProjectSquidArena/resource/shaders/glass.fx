// Tinted transparent glass with Fresnel response and screen-capture reflection approximation.
float4x4 gWorld : WORLD;float4x4 gWorldViewProjection : WORLDVIEWPROJECTION;float4x4 gViewProjection : VIEWPROJECTION;float3 gCameraPosition : CAMERAPOSITION;
float gAlpha=0.38;float gReflect=0.7;float gTime : TIME;
texture gTexture0 < string textureState="0,Texture"; >;texture gScreen;
sampler S0=sampler_state { Texture=(gTexture0); MinFilter=Anisotropic; MagFilter=Linear; MipFilter=Linear; };
sampler SS=sampler_state { Texture=(gScreen); MinFilter=Linear; MagFilter=Linear; MipFilter=None; AddressU=Clamp; AddressV=Clamp; };
struct VI{float3 Pos:POSITION0;float3 Normal:NORMAL0;float4 Color:COLOR0;float2 UV:TEXCOORD0;};
struct VO{float4 Pos:POSITION0;float4 Color:COLOR0;float2 UV:TEXCOORD0;float3 WP:TEXCOORD1;float3 N:TEXCOORD2;float4 Clip:TEXCOORD3;};
VO VS(VI i){VO o=(VO)0;o.Pos=mul(float4(i.Pos,1),gWorldViewProjection);o.Clip=o.Pos;o.WP=mul(float4(i.Pos,1),gWorld).xyz;o.N=normalize(mul(i.Normal,(float3x3)gWorld));o.UV=i.UV;o.Color=i.Color;return o;}
float4 PS(VO i):COLOR0{
 float4 tex=tex2D(S0,i.UV);float3 N=normalize(i.N);float3 V=normalize(gCameraPosition-i.WP);float3 R=reflect(-V,N);
 float4 cp=mul(float4(i.WP+R*24,1),gViewProjection);float2 uv=cp.xy/max(cp.w,.001)*float2(.5,-.5)+.5;
 float edge=saturate(min(min(uv.x,uv.y),min(1-uv.x,1-uv.y))*15);float valid=edge*step(.01,cp.w);
 float3 refl=tex2D(SS,uv+float2(sin(gTime+i.WP.x),cos(gTime+i.WP.y))*.0008).rgb;
 float fres=pow(1-saturate(dot(N,V)),3.0);float3 tint=float3(.26,.52,.61);
 float3 color=lerp(tint*tex.rgb,lerp(tint,refl,valid),saturate(gReflect*(.24+.76*fres)));
 float a=saturate(gAlpha*(.72+.28*fres)+tex.a*.10);return float4(color,a);
}
technique GlassFresnel { pass P0 { AlphaBlendEnable=TRUE; SrcBlend=SRCALPHA; DestBlend=INVSRCALPHA; ZWriteEnable=FALSE; VertexShader=compile vs_3_0 VS(); PixelShader=compile ps_3_0 PS(); } }
technique Fallback { pass P0 { } }
