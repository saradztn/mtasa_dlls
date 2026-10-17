// Restrained emissive LED pass; it brightens material pixels but does not claim to cast real light.
float4x4 gWorldViewProjection:WORLDVIEWPROJECTION;float gStrength=1.35;float gTime:TIME;
texture gTexture0 < string textureState="0,Texture"; >;
sampler S0=sampler_state{Texture=(gTexture0);MinFilter=Linear;MagFilter=Linear;MipFilter=Linear;};
struct VI{float3 Pos:POSITION0;float4 Color:COLOR0;float2 UV:TEXCOORD0;};struct VO{float4 Pos:POSITION0;float4 Color:COLOR0;float2 UV:TEXCOORD0;};
VO VS(VI i){VO o;o.Pos=mul(float4(i.Pos,1),gWorldViewProjection);o.Color=i.Color;o.UV=i.UV;return o;}
float4 PS(VO i):COLOR0{float4 c=tex2D(S0,i.UV)*i.Color;float pulse=.93+.07*sin(gTime*1.8);return float4(c.rgb*gStrength*pulse,c.a);}
technique Emissive{pass P0{VertexShader=compile vs_2_0 VS();PixelShader=compile ps_2_0 PS();}}
technique Fallback{pass P0{}}
