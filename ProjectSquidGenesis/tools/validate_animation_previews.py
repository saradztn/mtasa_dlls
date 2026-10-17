from pathlib import Path
import json,hashlib
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'tests/animation_preview_results.json').read_text());manifest={c['name']:c for c in json.loads((ROOT/'source_assets/animations/manifest.json').read_text())}
assert report['source_sha256']==hashlib.sha256((ROOT/'source_assets/animations/GenesisAnimations.blend').read_bytes()).hexdigest()
results=[]
for p in report['previews']:
    path=ROOT/p['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==p['sha256']
    with Image.open(path) as im:
        assert im.format=='GIF' and im.size==tuple(p['dimensions']) and im.n_frames==p['frames'] and im.n_frames>=2
        duration=0
        for index in range(im.n_frames):im.seek(index);im.load();duration+=im.info.get('duration',0)
        assert duration==p['playback_duration_ms']==round(manifest[p['name']]['seconds']*1000)
        assert len(p['normalized_sample_times'])==p['rendered_samples']>=im.n_frames
        results.append({'name':p['name'],'decoded_frames':im.n_frames,'rendered_samples':p['rendered_samples'],'duration_ms':duration,'status':'PASS'})
(ROOT/'tests/animation_preview_integrity_results.json').write_text(json.dumps({'status':'PASS','scope':'GIF decoding/timing/hash validation only; not human motion acceptance','source_sha256':report['source_sha256'],'results':results},indent=2));print(results)
