# Map Construction Algorithms
Enabled by the ubiquitous generation of geo-referenced tracking data, there has been a recent surge of algorithms that construct street maps from tracking data.

However, visual inspection is still the most common approach to evaluate the quality of the algorithms, and cross-comparison of different algorithms is very rare, since algorithms and constructed maps are generally not publicly available. There is a lack of benchmark data, and quantitative evaluation with suitable distance measures has just recently begun.

This repository will provide access to

* a set of map generation algorithms,
* data sets including tracking data as well as respective map datasets, and
* various distance measures to assess the quality of the constructed maps.

As they become available, we encourage interested scientists and developers to add their source code to this site.

## Citing the work

Should you use the source code and/or data from this site, please cite also the following paper:

> M. Ahmed, S. Karagiorgou, D. Pfoser, and C. Wenk. 
> A Comparison and Evaluation of Map Construction Algorithms. 
> GeoInformatica, 19(3):601-632, 2015.

> DOI: 10.1007/s10707-014-0222-6 - [paper](http://arxiv.org/pdf/1402.5138.pdf)

##  Web page

Refer to the [project Web page](https://pfoser.github.io/mapconstruction/) for more details.

## Visual comparison after an end-to-end run

See [Athens small end-to-end walkthrough (中文)](docs/e2e-athens-small.md)
for environment setup, map construction, bidirectional Hausdorff evaluation,
and visual comparison, with reproducible commands.

After generating the Athens small map in `runs/e2e/generated/`, create an
offline comparison with Python 3 (no additional packages required):

```bash
python3 scripts/visualize_e2e.py --run-dir runs/e2e
open runs/e2e/visualization/comparison.html
```

The four synchronized views show input trajectories, the OSM reference map,
the generated map, and an overlay. Drag to pan, scroll or use the buttons to
zoom, and toggle the layers. `runs/e2e/visualization/overlay.svg` is also
generated for export. Rerun the command whenever map outputs change.

The defaults expect `input/athens_small/trips/`,
`input/map_athens_small/athens_small_{vertices,edges}_osm.txt`, and
`generated/athens_{vertices,edges}.txt` under the run directory.
For other datasets or algorithms, use `--tracks`, `--reference-vertices`,
`--reference-edges`, `--generated-vertices`, and `--generated-edges` to specify
the corresponding paths (see `--help`). All layers must use the same projected
coordinate system. Both comma- and whitespace-separated map files are accepted.

The viewer displays the full data extent, which may differ from an evaluation's
bounding box. It draws original trajectories before algorithm preprocessing
and deduplicates reverse edges for display. Visual inspection complements
the distance metrics; it does not measure connectivity or single-way restrictions.

### Comparison on a street-map basemap

For Athens, the same command also generates `runs/e2e/visualization/basemap.html`:

```bash
open runs/e2e/visualization/basemap.html
```

It shows three synchronized maps: original GPS tracks, generated roads, and
generated roads over the historical OSM reference. Checkboxes toggle the
overlays and the current OpenStreetMap street basemap. Internet access is
required for Leaflet 1.9.4, proj4js 2.12.1 and visible OSM tiles; the original
`comparison.html` remains fully offline.

Athens coordinates are interpreted as GGRS87 / Greek Grid (EPSG:2100), then
converted to WGS84. This interpretation was checked against OSM node 35487981:
the dataset coordinate (483873.155864, 4217312.884405) transforms to
(longitude 23.81775899, latitude 38.10608119), about 3 m from that node's current
OSM position. This is a plausibility check, not a survey-level accuracy claim.
The current basemap can differ from the historical reference data.

Other cities need an explicitly verified source CRS: pass `--basemap-crs`
with a proj4 definition (EPSG:2100 is bundled). Do not apply the Athens default
to Chicago or Berlin. Without a source CRS, non-Athens runs only generate the
offline projected-coordinate comparison.
