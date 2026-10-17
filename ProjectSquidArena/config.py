"""Single configuration source: arena offsets, dimensions and AI tuning."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MODEL_BASE=15000
ARENAS={
 'tug': {'name':'Tug-of-War Arena','dimension':827,'origin':[8000.0,8000.0,220.0],'center':[0,0,0],'entry':[-16.0,0.0,1.2],'ai':[15.0,0.0,1.2],'deck_z':0},
 'bridge': {'name':'Glass Bridge Arena','dimension':828,'origin':[8000.0,8200.0,220.0],'center':[0,0,0],'entry':[0.0,-39.0,1.0],'ai':[4.5,-39.0,1.0],'deck_z':0,'first_panel_y':-32,'step':3.8,'steps':18},
}
AI={'tug_team_size':3,'tug_pressure_per_second':0.23,'bridge_skill':0.79}
DEFAULTS={'quality':'high','wetness':0.88,'reflection':0.46}
