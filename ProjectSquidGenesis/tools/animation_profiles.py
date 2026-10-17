"""Editable metre-space motion/contact contracts, independent of Blender.
+Y forward, +Z up. Root values are WORLD/rig-space, not a root bone's local axes.
"""
import math
TW=['Ready','GrabRope','PullLoop','StrongPull','Resist','Stumble','Recovery','Release','Victory','Fall']
GB=['IdleBalance','CautiousWalk','TestPanel','WeightShift','Hesitate','ShortStep','BalanceRecover','Slip','Jump','Fall']
NAMES=['TW_'+x for x in TW]+['GB_'+x for x in GB]
LOOPS={'TW_Ready','TW_PullLoop','TW_Resist','GB_IdleBalance','GB_CautiousWalk'}
GRIP_WRISTS=[[0,.28,1.06],[0,.42,1.06]]
def smooth(t):return t*t*(3-2*t)
def clamp(t):return max(0,min(1,t))
def duration(name):return 3 if name.endswith(('Victory','CautiousWalk')) else 1.2 if name in ('GB_Jump','GB_Slip','TW_Stumble') else 2

def profile(name,t):
    wave=math.sin(math.tau*t);s=smooth(t);p=math.sin(math.pi*t)**2
    tug=name.startswith('TW')
    root=[0,.08,-.14] if tug else [0,0,-.10]
    hands=[h[:] for h in GRIP_WRISTS] if tug else [[-.42,.05,1.2],[.42,.05,1.2]]
    feet=[[-.16,-.18,.10],[.16,.18,.10]];lean=0;pitch=[0,0]
    if name=='TW_Ready':root[2]-=.008*wave
    elif name=='TW_GrabRope':
        lean=.10*p;root[2]-=.035*p
        for i,h in enumerate(hands):h[:]=[(i*2-1)*.35*(1-s),.06+(GRIP_WRISTS[i][1]-.06)*s,1+.06*s]
    elif name=='TW_PullLoop':root[1]-=.075*p;root[2]-=.03*p;lean=-.10*p
    elif name=='TW_StrongPull':root[1]-=.11*p;root[2]-=.10*p;lean=-.15*p
    elif name=='TW_Resist':root[1]-=.06;root[2]-=.04+.008*wave;lean=-.12+.012*wave
    elif name=='TW_Stumble':
        u=clamp((t-.15)/.55);root[0]=.12*p;root[1]+=.12*s
        feet[1][1]+=.25*smooth(u);feet[1][2]+=.09*math.sin(math.pi*u)**2;hands[1][0]+=.18*p
    elif name=='TW_Recovery':
        root[1]+=.12*(1-s);root[2]-=.035*p
        feet[1][1]+=.25*(1-s);feet[1][2]+=.09*p
    elif name=='TW_Release':
        for i,h in enumerate(hands):h[0]=(i*2-1)*.35*s;h[1]=h[1]*(1-s)+.03*s;h[2]-=.10*s
    elif name=='TW_Victory':
        for i,h in enumerate(hands):h[:]=[(i*2-1)*.35*s,h[1]*(1-s)+.08*s,1.06+.79*s];pitch[i]=.95*s
        root[2]+=.06*p
    elif name.endswith('_Fall'):
        root=[(.12 if tug else .22)*s,.35*s,(-.14 if tug else -.10)-1.2*s]
        lean=(.65 if tug else .48)*s
        for i in range(2):
            feet[i][1]+=.4*s;feet[i][2]-=1.2*s
            hands[i]=[root[0]+(i*2-1)*((.33 if tug else .42)+.10*p),root[1]+.15,1.24+root[2]]
    elif name=='GB_IdleBalance':root[0]=.018*wave;hands[0][2]+=.045*wave;hands[1][2]-=.045*wave
    elif name=='GB_CautiousWalk':
        # In-place. A consumer translating +.88m/cycle cancels stance-foot travel.
        for i in range(2):
            phase=(t+i*.5)%1
            if phase<=.5:feet[i][1]=.22-.88*phase
            else:
                u=(phase-.5)*2
                # Cubic Hermite swing matches stance velocity at both contacts.
                feet[i][1]=-.22*(2*u**3-3*u*u+1)+.22*(-2*u**3+3*u*u)-.44*(u**3-2*u*u+u)-.44*(u**3-u*u)
                feet[i][2]+=.09*math.sin(math.pi*u)**2
            hands[i][1]=.05-.07*math.cos(math.tau*phase)
        root[2]+=.012*(1-math.cos(2*math.tau*t))
    elif name=='GB_TestPanel':
        root[0]=-.05*p;root[1]=.04*p;root[2]-=.01*p;lean=.06*p
        if t<.35:u=t/.35;feet[1][1]+=.24*smooth(u);feet[1][2]+=.10*math.sin(math.pi*u)**2
        elif t<=.65:feet[1][1]+=.24
        else:u=(t-.65)/.35;feet[1][1]+=.24*(1-smooth(u));feet[1][2]+=.10*math.sin(math.pi*u)**2
    elif name=='GB_WeightShift':root[0]=-.09+.18*s;hands[1][2]+=.08*p
    elif name=='GB_Hesitate':feet[1][1]+=.13*p;feet[1][2]+=.05*p;root[1]=.04*p;hands[0][1]+=.12*p
    elif name=='GB_ShortStep':feet[1][1]+=.36*s;feet[1][2]+=.09*p;root[1]=.16*s;root[2]-=.01*p
    elif name=='GB_BalanceRecover':root[0]=.15*(1-s);hands[0][0]-=.12*(1-s);root[2]-=.025*p
    elif name=='GB_Slip':feet[1][0]+=.3*s;feet[1][1]+=.25*s;root[0]=.12*s;root[2]-=.12*s;hands[0][2]+=.20*p
    elif name=='GB_Jump':
        if t<=.2:
            u=t/.2;travel=0;lift=0;crouch=.08*smooth(u)
        elif t<.8:
            u=(t-.2)/.6;travel=.65*smooth(u);lift=.34*math.sin(math.pi*u);crouch=.08
        else:
            u=(t-.8)/.2;travel=.65;lift=0;crouch=.08*(1-smooth(u))
        root[1]=travel;root[2]+=-crouch+lift
        for h in hands:h[1]+=travel+.20*p;h[2]+=.20*p
        for f in feet:f[1]+=travel;f[2]+=lift
    else:raise ValueError(name)
    return {'root':root,'hands':hands,'feet':feet,'lean':lean,'hand_pitch':pitch}

def contract(name):
    both={side:[[0,1]] for side in ['L','R']};none={side:[] for side in ['L','R']}
    if name in ('TW_Stumble','TW_Recovery','GB_TestPanel','GB_Hesitate','GB_ShortStep','GB_Slip'):
        planted={'L':[[0,1]],'R':[]}
        if name=='TW_Stumble':planted['R']=[[0,.15],[.70,1]]
        elif name=='GB_TestPanel':planted['R']=[[0,0],[.35,.65],[1,1]]
        elif name!='GB_Slip':planted['R']=[[0,0],[1,1]]
    elif name=='GB_Jump':planted={side:[[0,.2],[.8,1]] for side in ['L','R']}
    elif name.endswith('_Fall'):planted=none
    elif name=='GB_CautiousWalk':planted={'L':[[0,.5]],'R':[[.5,1]]}
    else:planted=both
    grip=[[0,1]] if name in ('TW_Ready','TW_PullLoop','TW_StrongPull','TW_Resist') else [[1,1]] if name in ('TW_GrabRope','TW_Recovery') else [[0,0]] if name in ('TW_Release','TW_Victory') else []
    return {'planted_windows_normalized':planted,'grip_windows_normalized':grip,'virtual_actor_translation_per_cycle':[0,.88,0] if name=='GB_CautiousWalk' else [0,0,0], 'contact_tolerance_m':.002,'target_tolerance_m':.002,'rope_axis':{'origin':[0,0,1.05],'direction':[0,1,0]},'in_place':name=='GB_CautiousWalk'}
