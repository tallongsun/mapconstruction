# Athens small：从轨迹到地图评价的端到端流程

本文记录本仓库跑通的流程：Athens small GPS 轨迹 → Ahmed 地图构建 →
与 OSM 参考路网进行双向 Hausdorff 评价 → 离线及真实地图底图对比。
所有命令在仓库根目录、同一终端中顺序执行。运行产物统一放入 `runs/e2e/`，
该目录被 Git 忽略，原始 ZIP 数据和算法源码不变。

## 1. 环境准备

需要 JDK（本次使用 Homebrew OpenJDK 17）、Python 3、unzip。
可视化生成器只使用 Python 标准库，不需要安装 matplotlib 或 pyproj。

macOS 上如果尚未安装 JDK：

```bash
brew install openjdk@17
export PATH="$(brew --prefix openjdk@17)/bin:$PATH"
java -version
javac -version
python3 --version
```

已经安装 JDK 的系统直接验证 `java` 和 `javac` 可用即可。
若 macOS 提示 `Unable to locate a Java Runtime`，说明当前终端尚未正确找到 JDK。

进入自己的仓库目录，例如：

```bash
cd /path/to/mapconstruction
```

## 2. 准备数据与目录

```bash
mkdir -p runs/e2e/input runs/e2e/bin/ahmed runs/e2e/bin/evaluation
mkdir -p runs/e2e/generated runs/e2e/paths runs/e2e/results
mkdir -p runs/e2e/paths-reverse runs/e2e/results-reverse

unzip -q -o data/tracks/tracks_athens_small.zip -d runs/e2e/input/
unzip -q -o data/maps/map_athens_small.zip -d runs/e2e/input/

find runs/e2e/input/athens_small/trips -type f -name '*.txt' | wc -l
wc -l runs/e2e/input/map_athens_small/athens_small_vertices_osm.txt \
      runs/e2e/input/map_athens_small/athens_small_edges_osm.txt
```

本次数据为 129 条轨迹、2694 个 OSM 顶点、3436 条 OSM 边。
轨迹每行是空格分隔的 `x y timestamp`，地图文件使用逗号分隔。
输入必须指向 `trips/`，不要把 LICENSE、`__MACOSX` 等文件一起交给算法。
再次解压会覆盖上述解压目录内的同名文件。

## 3. 编译和运行 Ahmed

```bash
javac -d runs/e2e/bin/ahmed algorithms/Ahmed/src/mapconstruction2/*.java

java -cp runs/e2e/bin/ahmed mapconstruction2.MapConstruction \
  runs/e2e/input/athens_small/trips/ \
  runs/e2e/generated/athens_ \
  150.0 false 4.0
```

参数分别是输入轨迹目录、输出文件名前缀、水平距离阈值 ε（150 米）、
是否包含高度（false）、高度差阈值（4 米）。150 米沿用仓库示例，
用于跑通流程，不代表该数据集的最优参数。

输出：

```text
runs/e2e/generated/athens_vertices.txt  # id,x,y,z
runs/e2e/generated/athens_edges.txt     # id,source,target
```

```bash
wc -l runs/e2e/generated/athens_vertices.txt runs/e2e/generated/athens_edges.txt
sed -n '1,5p' runs/e2e/generated/athens_vertices.txt
sed -n '1,5p' runs/e2e/generated/athens_edges.txt
```

本次已有产物包含 245 个顶点和 448 行边；绘图时将反向重复边合并为 224 条。
算法通过 `folder.listFiles()` 读取轨迹，没有固定排序，因此这些数字是本次运行记录，
并非所有环境的严格验收值。重新运行会覆盖同名前缀的输出。

## 4. 编译评价程序

```bash
javac -d runs/e2e/bin/evaluation \
  evaluation/pathbaseddistance/MapMatching/src/mapmatchingbasics/*.java \
  evaluation/pathbaseddistance/MapMatching/src/generatepaths/*.java \
  evaluation/pathbaseddistance/MapMatching/src/mapmatching/*.java \
  evaluation/pathbaseddistance/MapMatching/src/benchmarkexperiments/*.java
```

旧 Java API 的 deprecated warning 不等于编译失败；遇到 `error` 应先处理。
Ahmed 输出可直接被该评价程序读取，额外的 z 列会被忽略，无需转换文件。

## 5. 正向评价：生成路网 → OSM

本次选择一个较小范围快速跑通：
`[483000,484000,4215000,4216500]`，顺序为 `[XLow,XHigh,YLow,YHigh]`。

```bash
java -cp runs/e2e/bin/evaluation \
  benchmarkexperiments.BenchmarkHausdorffExperiments \
  athens \
  runs/e2e/generated/athens_vertices.txt \
  runs/e2e/generated/athens_edges.txt false \
  runs/e2e/input/map_athens_small/athens_small_vertices_osm.txt \
  runs/e2e/input/map_athens_small/athens_small_edges_osm.txt false \
  '[483000,484000,4215000,4216500]' \
  runs/e2e/paths/ runs/e2e/results/
```

两个 `false` 表示按无向图读取。参数中的目录尾部 `/` 要保留，旧代码直接拼接路径。
程序将图 1 拆成 `LineSegment` 路径，为每条边计算到图 2 的覆盖距离。
路径文件分到 0～4 五个子目录，结果也分为五个文件。

路径生成程序会删除其指定路径子目录中的旧文件，因此始终使用上述专用运行目录。
图的 bounding box 过滤保留框内顶点及两端都在框内的边，并不是严格的几何裁剪。
如需全图评价，将范围参数改为 `'[]'`；正反向应保持同一范围，结果可能与本次不同。

## 6. 反向评价：OSM → 生成路网

交换图 1 和图 2，使用独立路径及结果目录：

```bash
java -cp runs/e2e/bin/evaluation \
  benchmarkexperiments.BenchmarkHausdorffExperiments \
  athens \
  runs/e2e/input/map_athens_small/athens_small_vertices_osm.txt \
  runs/e2e/input/map_athens_small/athens_small_edges_osm.txt false \
  runs/e2e/generated/athens_vertices.txt \
  runs/e2e/generated/athens_edges.txt false \
  '[483000,484000,4215000,4216500]' \
  runs/e2e/paths-reverse/ runs/e2e/results-reverse/
```

正向距离帮助发现偏移、多余道路，反向距离帮助发现真实道路未被覆盖的位置。
后者也受轨迹覆盖范围影响，不能把所有缺失都直接归因于算法。
“评价方向”与道路是否单向通行是两个不同概念。

## 7. 汇总评价结果

结果每行四列：`路径文件名 点数 距离 路径长度`。
距离单位为米，程序搜索整数 ε。项目定义的整图指标是第三列最大值；
平均值是辅助统计，并不是项目定义的 graph distance。

```bash
for result_dir in runs/e2e/results runs/e2e/results-reverse; do
  awk -v label="$result_dir" '
    NF == 4 { n++; sum += $3; if ($3 > max) max = $3 }
    END {
      if (n == 0) { print label, "ERROR: no results"; exit 1 }
      printf "%s: paths=%d max=%.1f m mean=%.4f m\n", label, n, max, sum/n
    }
  ' "$result_dir"/LineSegment/outputHausdorff*.txt
done
```

2026-09-09 本次已有运行产物的统计：

| 方向 | 路径数 | 最大距离 | 平均距离 |
| --- | ---: | ---: | ---: |
| Ahmed → OSM | 104 | 60 m | 18.8269 m |
| OSM → Ahmed | 1180 | 323 m | 97.3881 m |

无向边可能以两个方向生成路径，路径数不等于去重后的道路数量。
程序搜索范围先为 1～1600，必要时扩展到 2400；若出现 2401，代表搜索范围内未找到
可行值，不应当作精确距离。完全重合的线段也可能报告 1，不能用是否输出 0 判断正确性。

## 8. 生成视觉对比

```bash
python3 scripts/visualize_e2e.py --run-dir runs/e2e
```

生成三个文件：

| 文件 | 用途 |
| --- | --- |
| `runs/e2e/visualization/comparison.html` | 离线四视图：轨迹、OSM、生成路网、叠加 |
| `runs/e2e/visualization/overlay.svg` | 可保存或放入报告的矢量叠加图 |
| `runs/e2e/visualization/basemap.html` | 真实街道底图上的三视图对比 |

macOS 打开：

```bash
open runs/e2e/visualization/comparison.html
open runs/e2e/visualization/basemap.html
```

其他系统可直接用浏览器打开 HTML。视图支持同步缩放、平移、图层开关。
底图版依赖联网加载 Leaflet、proj4js 和可见范围的 OpenStreetMap 瓦片；
离线版没有外部依赖。每次生成地图后重新运行 Python 命令，即可刷新可视化数据。

Athens 默认按 EPSG:2100（GGRS87 / Greek Grid）转换到 WGS84。
该解释通过仓库中的 OSM 节点 35487981 与在线同编号节点核对：转换后约相差 3 米。
这只是位置合理性检查，不是测绘精度验证。其他城市需核实投影，不能沿用 Athens 的 CRS。

可视化显示完整范围，评价使用的是上文的小 bounding box，两者范围不同。
在线底图是当前道路，仓库参考路网较旧；道路增改可能造成差异。
轨迹图展示原始输入，尚未经过 Ahmed 的点间距及时间间隔过滤。

## 9. 后续实验

跑不同 ε 时使用独立输出前缀，并为每组实验分配独立评价目录，避免覆盖结果。
可以通过以下参数将可视化应用到其他算法或数据文件：

```bash
python3 scripts/visualize_e2e.py --help
```

主要可指定 `--tracks`、`--reference-vertices`、`--reference-edges`、
`--generated-vertices`、`--generated-edges`、`--basemap-crs`。
每层数据必须使用相同的投影坐标系；不同城市的真实底图需提供核实过的 proj4 定义。
