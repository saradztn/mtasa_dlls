// D3D9 Effects; MTA automatic semantics. Not SSR/ray tracing/scene reflection.
float4x4 gWorld : WORLD;
float4x4 gWorldViewProjection : WORLDVIEWPROJECTION;
float3 gCameraPosition : CAMERAPOSITION;
texture gTexture0 < string textureState = "0,Texture"; >;
texture gNormal;
texture gSurface;
float gWetness=0.65;
float gReflection=1;
float gNormalScale=1;
float3 gLight0; float3 gLight1; float3 gLight2; float3 gLight3;
float3 gColor0; float3 gColor1; float3 gColor2; float3 gColor3;
float gEmissive=0;
sampler Base = sampler_state {Texture=<gTexture0>; MinFilter=Linear;MagFilter=Linear;MipFilter=Linear;AddressU=Wrap;AddressV=Wrap;};
sampler Normal = sampler_state {Texture=<gNormal>; MinFilter=Linear;MagFilter=Linear;MipFilter=Linear;AddressU=Wrap;AddressV=Wrap;};
sampler Surface = sampler_state {Texture=<gSurface>; MinFilter=Linear;MagFilter=Linear;MipFilter=Linear;AddressU=Wrap;AddressV=Wrap;};
struct VI {float3 p:POSITION0;float3 n:NORMAL0;float2 uv:TEXCOORD0;float4 color:COLOR0;};
struct PI {float4 p:POSITION0;float3 w:TEXCOORD0;float3 n:TEXCOORD1;float2 uv:TEXCOORD2;float4 color:COLOR0;};
PI VS(VI v) {PI o;o.p=mul(float4(v.p,1),gWorldViewProjection);o.w=mul(float4(v.p,1),gWorld).xyz;o.n=normalize(mul(v.n,(float3x3)gWorld));o.uv=v.uv;o.color=v.color;return o;}
float3 Light(float3 pos,float3 color,float3 w,float3 n,float3 view,float rough,float metal,float3 base,float wet) {
    float3 delta=pos-w;float d=max(length(delta),.01);float3 l=delta/d;
    float attenuation=pow(saturate(1-d/26),2);
    float ndl=saturate(dot(n,l));float3 halfV=normalize(l+view);
    float power=lerp(8,160,1-rough);float fres=pow(1-saturate(dot(n,view)),5);
    float3 f0=lerp(float3(.04,.04,.04),base,metal);
    float3 spec=(f0+(1-f0)*fres)*pow(saturate(dot(n,halfV)),power)*(power+2)/24;
    return color*attenuation*(base*ndl*.8+spec*gReflection*(.3+wet));
}
float4 PS(PI p):COLOR0 {
    float4 base=tex2D(Base,p.uv);float4 surf=tex2D(Surface,p.uv);
    float3 n=normalize(p.n);float3 detail=tex2D(Normal,p.uv).xyz*2-1;
    // Derivative cotangent frame supports authored UVs on walls and floors.
    float3 dp1=ddx(p.w),dp2=ddy(p.w);float2 duv1=ddx(p.uv),duv2=ddy(p.uv);
    float3 dp2perp=cross(dp2,n),dp1perp=cross(n,dp1);
    float3 t=dp2perp*duv1.x+dp1perp*duv2.x;float3 b=dp2perp*duv1.y+dp1perp*duv2.y;
    float invLen=rsqrt(max(max(dot(t,t),dot(b,b)),.00001));
    n=normalize(n+gNormalScale*(detail.x*t+detail.y*b)*invLen*.35);
    float wet=saturate(gWetness*surf.b);float rough=clamp(lerp(lerp(ROUGH,surf.r,.9), .08,wet),.08,1);
    float3 albedo=base.rgb*(1-wet*POROSITY*.32);float3 view=normalize(gCameraPosition-p.w);
    float metal=lerp(METAL,surf.a,.9);float3 c=albedo*(.28+.65*p.color.rgb)*surf.g;
    c+=Light(gLight0,gColor0,p.w,n,view,rough,metal,albedo,wet);
    c+=Light(gLight1,gColor1,p.w,n,view,rough,metal,albedo,wet);
    c+=Light(gLight2,gColor2,p.w,n,view,rough,metal,albedo,wet);
    c+=Light(gLight3,gColor3,p.w,n,view,rough,metal,albedo,wet);
    c+=base.rgb*gEmissive;
    float alpha=base.a;
#if GLASS
    float fres=pow(1-abs(dot(n,view)),5);alpha=clamp(.26+fres*.5,.26,.8);c+=float3(.035,.09,.1)*fres;
#endif
    return float4(c/(1+c*.35),alpha*p.color.a);
}
technique genesis {pass P0 {VertexShader=compile vs_3_0 VS();PixelShader=compile ps_3_0 PS();AlphaBlendEnable=TRUE;SrcBlend=SRCALPHA;DestBlend=INVSRCALPHA;
#if GLASS
ZWriteEnable=FALSE;
#else
ZWriteEnable=TRUE;
#endif
}}
// No silent fixed-function technique: dxCreateShader failure is reported in Lua.
