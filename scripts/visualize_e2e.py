#!/usr/bin/env python3
"""Build offline HTML and SVG comparisons from map-construction outputs."""
import argparse
import html
import json
import math
from pathlib import Path


def rows(path):
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if line.strip():
            yield number, line.replace(',', ' ').split()


def read_map(vertices_path, edges_path):
    vertices = {}
    for _, values in rows(vertices_path):
        point = tuple(map(float, values[1:3]))
        if len(point) != 2 or not all(map(math.isfinite, point)):
            raise ValueError(f'Invalid coordinate: {vertices_path}')
        vertices[values[0]] = point
    edges, seen = [], set()
    for _, values in rows(edges_path):
        a, b = values[1:3]
        key = tuple(sorted((a, b)))
        if a not in vertices or b not in vertices:
            raise ValueError(f'Edge references unknown vertex: {edges_path}: {a}, {b}')
        if a != b and key not in seen:
            edges.append([vertices[a], vertices[b]])
            seen.add(key)
    if not edges:
        raise ValueError(f'No edges: {edges_path}')
    return edges


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=Path('runs/e2e'))
    parser.add_argument('--city', default='athens_small', help='Extracted track directory name')
    parser.add_argument('--prefix', default='athens', help='Generated map filename prefix')
    parser.add_argument('--tracks', type=Path)
    parser.add_argument('--reference-vertices', type=Path)
    parser.add_argument('--reference-edges', type=Path)
    parser.add_argument('--generated-vertices', type=Path)
    parser.add_argument('--generated-edges', type=Path)
    parser.add_argument('--basemap-crs', help='Source EPSG:2100 or a proj4 definition; defaults to EPSG:2100 for Athens')
    args = parser.parse_args()
    run = args.run_dir
    track_dir = args.tracks or run / 'input' / args.city / 'trips'
    reference = run / 'input' / ('map_' + args.city)
    ground = read_map(
        args.reference_vertices or reference / (args.city + '_vertices_osm.txt'),
        args.reference_edges or reference / (args.city + '_edges_osm.txt'))
    generated = read_map(
        args.generated_vertices or run / 'generated' / (args.prefix + '_vertices.txt'),
        args.generated_edges or run / 'generated' / (args.prefix + '_edges.txt'))
    tracks = []
    for path in sorted(track_dir.glob('*.txt')):
        points = [tuple(map(float, values[:2])) for _, values in rows(path)]
        if any(len(p) != 2 or not all(map(math.isfinite, p)) for p in points):
            raise ValueError(f'Invalid track: {path}')
        if len(points) >= 2:
            tracks.append(points)
    if not tracks:
        raise ValueError(f'No trajectories in {track_dir}')
    points = [p for collection in (tracks, ground, generated) for segment in collection for p in segment]
    xmin, xmax = min(p[0] for p in points), max(p[0] for p in points)
    ymin, ymax = min(p[1] for p in points), max(p[1] for p in points)
    extent = max(xmax - xmin, ymax - ymin, 1)
    scale = 900 / extent
    width, height = (xmax - xmin) * scale + 40, (ymax - ymin) * scale + 40

    def path_data(lines):
        return ' '.join(' '.join(
            f'{"M" if i == 0 else "L"}{20 + (x-xmin)*scale:.3f},{20 + (ymax-y)*scale:.3f}'
            for i, (x, y) in enumerate(line)) for line in lines)

    paths = {name: path_data(lines) for name, lines in
             [('tracks', tracks), ('reference', ground), ('generated', generated)]}
    colors = {'tracks': '#81909e', 'reference': '#2276b9', 'generated': '#e15a24'}
    title = html.escape(args.city + ' · Map construction')

    def svg(layers):
        body = ''.join(f'<path class="{name}" d="{paths[name]}" fill="none" '
                       f'stroke="{colors[name]}" stroke-width="{0.8 if name == "tracks" else 1.5}" '
                       f'opacity="{0.4 if name == "tracks" else 0.85}" '
                       'vector-effect="non-scaling-stroke"/>' for name in layers)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.3f} {height:.3f}" '
                f'role="img" aria-label="{title}: {", ".join(layers)}">'
                f'<rect width="100%" height="100%" fill="white"/>{body}</svg>')

    panels = [('GPS 轨迹', ['tracks']), ('OSM 参考路网', ['reference']),
              ('生成路网', ['generated']), ('叠加对比', ['tracks', 'reference', 'generated'])]
    figures = ''.join(f'<figure><figcaption>{label}</figcaption>{svg(layers)}</figure>'
                      for label, layers in panels)
    template = '''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
body{font:15px/1.6 system-ui,sans-serif;margin:24px;background:#f3f6f9;color:#172c40}
h1{font-size:24px;margin:0}p{margin:8px 0}header,footer{max-width:1500px;margin:auto}
.controls{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin:16px 0}
button{font:inherit;background:white;border:1px solid #aebdca;border-radius:5px;padding:5px 14px;cursor:pointer}
main{max-width:1500px;margin:auto;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
figure{margin:0;background:white;border:1px solid #ccd6df;border-radius:7px;overflow:hidden}
figcaption{padding:10px 14px;font-weight:600;border-bottom:1px solid #e4eaf0}
svg{display:block;width:100%;height:65vh;min-height:320px;cursor:grab;touch-action:none}
svg:active{cursor:grabbing}footer{color:#526779;font-size:13px;margin-top:14px}
label{white-space:nowrap}@media(max-width:1000px){main{grid-template-columns:repeat(2,minmax(0,1fr))}svg{height:50vh}}
@media(max-width:550px){body{margin:12px}main{grid-template-columns:1fr}}
</style>
<header><h1>__TITLE__</h1>
<p>__COUNTS__</p>
<div class="controls"><button id="in">放大 +</button><button id="out">缩小 −</button><button id="reset">重置范围</button>
<label><input type="checkbox" data-layer="tracks" checked> 灰：轨迹</label>
<label><input type="checkbox" data-layer="reference" checked> 蓝：OSM</label>
<label><input type="checkbox" data-layer="generated" checked> 橙：生成路网</label></div>
<p>拖动任一视图同步平移；滚轮同步缩放。全部视图使用相同范围和等比例坐标。</p></header>
<main>__FIGURES__</main>
<footer>__EXTENT__<br>显示完整数据范围；评价若使用 bounding box，其统计范围可能更小。轨迹为原始输入，尚未经过构建算法的过滤。
无向重复边仅在绘图时去重；显示的是道路几何，不表示通行方向。此图不使用在线底图。</footer>
<script>
const plots=[...document.querySelectorAll('svg')];
const original=plots[0].getAttribute('viewBox').split(' ').map(Number);let view=[...original];
function draw(){plots.forEach(s=>s.setAttribute('viewBox',view.join(' ')));}
function zoom(f){const next=view[2]*f;if(next<original[2]/200||next>original[2]*5)return;
view=[view[0]+view[2]*(1-f)/2,view[1]+view[3]*(1-f)/2,view[2]*f,view[3]*f];draw();}
document.getElementById('in').onclick=()=>zoom(.8);
document.getElementById('out').onclick=()=>zoom(1.25);
document.getElementById('reset').onclick=()=>{view=[...original];draw();};
document.querySelectorAll('[data-layer]').forEach(input=>input.onchange=()=>{
document.querySelectorAll('path.'+input.dataset.layer).forEach(p=>p.style.display=input.checked?'':'none');});
plots.forEach(s=>{
let drag=null;
s.addEventListener('wheel',e=>{e.preventDefault();zoom(e.deltaY>0?1.1:1/1.1);},{passive:false});
s.addEventListener('pointerdown',e=>{if(e.button!==0)return;s.setPointerCapture(e.pointerId);drag=[e.clientX,e.clientY];});
s.addEventListener('pointermove',e=>{if(!drag)return;const r=s.getBoundingClientRect();
const unit=Math.max(view[2]/r.width,view[3]/r.height);
view[0]-=(e.clientX-drag[0])*unit;view[1]-=(e.clientY-drag[1])*unit;drag=[e.clientX,e.clientY];draw();});
s.addEventListener('pointerup',()=>drag=null);s.addEventListener('pointercancel',()=>drag=null);
});
</script></html>'''
    page = template.replace('__TITLE__', title).replace('__FIGURES__', figures)
    page = page.replace('__COUNTS__', f'{len(tracks)} 条轨迹 · {len(ground)} 条参考边 · {len(generated)} 条生成边（无向去重）')
    page = page.replace('__EXTENT__', f'投影坐标，单位米。X: {xmin:.1f} – {xmax:.1f}；Y: {ymin:.1f} – {ymax:.1f}。')
    output = run / 'visualization'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'comparison.html').write_text(page)
    (output / 'overlay.svg').write_text(svg(['tracks', 'reference', 'generated']))
    crs = args.basemap_crs or ('EPSG:2100' if args.city.startswith('athens') else None)
    if crs:
        payload = json.dumps(dict(crs=crs, tracks=tracks, reference=ground, generated=generated),
                             separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
        template_path = Path(__file__).with_name('basemap_comparison.html')
        basemap = template_path.read_text().replace('__TITLE__', title).replace('__DATA__', payload)
        (output / 'basemap.html').write_text(basemap)
        print(f'Basemap: {(output / "basemap.html").resolve()} (source CRS: {crs})')
    print(f'HTML: {(output / "comparison.html").resolve()}')
    print(f'SVG:  {(output / "overlay.svg").resolve()}')
    print(f'Tracks: {len(tracks)}; reference edges: {len(ground)}; generated edges: {len(generated)}')


if __name__ == '__main__':
    main()
