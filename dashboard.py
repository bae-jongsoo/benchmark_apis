import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pathlib import Path
import yaml
import json

RESULTS_DIR = Path("results")
CONFIG_PATH = Path("config.yaml")

COLORS = {
    "django-4w": "#2ecc71",
    "django-32w": "#f39c12",
    "fastapi-2w": "#3498db",
    "fastapi-4w": "#9b59b6",
    "fastapi-4w-sync": "#1abc9c",
    "fastapi-4w-async": "#e74c3c",
}

st.set_page_config(page_title="Django vs FastAPI Benchmark", layout="wide")
st.title("Django Ninja vs FastAPI Benchmark")

config = yaml.safe_load(open(CONFIG_PATH))

scenarios = {}
for scenario_name, cfgs in config.get("phase1_scenarios", {}).items():
    scenarios[f"Phase 1: {scenario_name}"] = {
        "phase": "phase1", "scenario": scenario_name,
        "configs": cfgs, "has_db_stats": False,
    }
for i, phase_key in enumerate([
    "phase2_scenarios", "phase3_scenarios", "phase4_scenarios", "phase5_scenarios",
    "phase6_scenarios", "phase7_scenarios", "phase8_scenarios", "phase9_scenarios", "phase10_scenarios",
], 2):
    for scenario_name, cfgs in config.get(phase_key, {}).items():
        has_db = phase_key == "phase4_scenarios"
        scenarios[f"Phase {i}: {scenario_name}"] = {
            "phase": f"phase{i}", "scenario": scenario_name,
            "configs": cfgs, "has_db_stats": has_db,
        }

selected = st.sidebar.selectbox("Scenario", list(scenarios.keys()))
scenario_info = scenarios[selected]


def load_csv(path):
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df = df[df["elapsed_seconds"] <= 30]
    return df


def create_dashboard(scenario_info):
    phase = scenario_info["phase"]
    scenario = scenario_info["scenario"]
    cfg_names = scenario_info["configs"]
    has_db_stats = scenario_info["has_db_stats"]

    k6 = {}
    stats = {}
    db_stats = {}
    for cn in cfg_names:
        df = load_csv(RESULTS_DIR / phase / f"{scenario}_{cn}.csv")
        if df is not None:
            k6[cn] = df
        df = load_csv(RESULTS_DIR / phase / f"stats_{scenario}_{cn}.csv")
        if df is not None:
            stats[cn] = df
        if has_db_stats:
            df = load_csv(RESULTS_DIR / phase / f"stats_db_{scenario}_{cn}.csv")
            if df is not None:
                db_stats[cn] = df

    if not k6:
        st.warning("No data found.")
        return

    first_k6 = list(k6.values())[0]
    x_data = [str(int(x)) for x in first_k6["elapsed_seconds"].tolist()]

    chart_defs = []

    # 1. RPS
    s = []
    for cn in cfg_names:
        if cn in k6:
            avg = k6[cn]["rps"].mean()
            s.append({"name": f"{cn} : {avg:.0f}", "data": k6[cn]["rps"].tolist(),
                       "color": COLORS.get(cn, "#999")})
    chart_defs.append(("RPS", "RPS", s, x_data))

    # 2. Latency P50
    s = []
    for cn in cfg_names:
        if cn in k6:
            s.append({"name": cn, "data": k6[cn]["latency_p50"].tolist(), "color": COLORS.get(cn, "#999")})
    chart_defs.append(("Latency P50 (ms)", "ms", s, x_data))

    # 3. Latency P95
    s = []
    for cn in cfg_names:
        if cn in k6:
            s.append({"name": cn, "data": k6[cn]["latency_p95"].tolist(), "color": COLORS.get(cn, "#999")})
    chart_defs.append(("Latency P95 (ms)", "ms", s, x_data))

    # 4. Latency P99
    s = []
    for cn in cfg_names:
        if cn in k6:
            s.append({"name": cn, "data": k6[cn]["latency_p99"].tolist(), "color": COLORS.get(cn, "#999")})
    chart_defs.append(("Latency P99 (ms)", "ms", s, x_data))

    # 5. Error Rate
    s = []
    for cn in cfg_names:
        if cn in k6:
            s.append({"name": cn, "data": k6[cn]["error_rate"].tolist(), "color": COLORS.get(cn, "#999")})
    chart_defs.append(("Error Rate (%)", "%", s, x_data))

    # 6. CPU
    s = []
    sx = None
    for cn in cfg_names:
        if cn in stats:
            s.append({"name": cn, "data": stats[cn]["cpu_percent"].tolist(), "color": COLORS.get(cn, "#999")})
            if sx is None:
                sx = [str(round(x, 1)) for x in stats[cn]["elapsed_seconds"].tolist()]
    if s:
        chart_defs.append(("CPU Usage (%)", "%", s, sx or x_data))

    # 7. Memory
    s = []
    for cn in cfg_names:
        if cn in stats:
            s.append({"name": cn, "data": [round(v, 1) for v in stats[cn]["memory_mb"].tolist()],
                       "color": COLORS.get(cn, "#999")})
    if s:
        chart_defs.append(("Memory (MB)", "MB", s, sx or x_data))

    if has_db_stats:
        s = []
        for cn in cfg_names:
            if cn in db_stats:
                s.append({"name": cn, "data": db_stats[cn]["cpu_percent"].tolist(),
                           "color": COLORS.get(cn, "#999")})
        if s:
            chart_defs.append(("DB CPU (%)", "%", s, sx or x_data))
        s = []
        for cn in cfg_names:
            if cn in db_stats:
                s.append({"name": cn, "data": [round(v, 1) for v in db_stats[cn]["memory_mb"].tolist()],
                           "color": COLORS.get(cn, "#999")})
        if s:
            chart_defs.append(("DB Memory (MB)", "MB", s, sx or x_data))

    n = len(chart_defs)
    chart_h = 300
    total_h = n * chart_h

    divs = ""
    inits = ""
    chart_ids = []

    for i, (title, y_name, series_list, xd) in enumerate(chart_defs):
        cid = f"c{i}"
        chart_ids.append(cid)
        divs += f'<div id="{cid}" style="width:100%;height:{chart_h}px;"></div>\n'

        series = []
        for s in series_list:
            serie = {
                "name": s["name"], "type": "line", "data": s["data"],
                "symbol": "none",
                "lineStyle": {"color": s["color"], "width": 2},
                "itemStyle": {"color": s["color"]},
            }
            if "dash" in s:
                dash_map = {"dash": [8, 4], "dot": [2, 4]}
                serie["lineStyle"]["type"] = dash_map.get(s["dash"], "solid")
            series.append(serie)

        option = {
            "title": {"text": title, "left": "center", "textStyle": {"fontSize": 13}},
            "tooltip": {
                "trigger": "axis",
                "order": "valueDesc",
                "axisPointer": {"type": "line"},
            },
            "legend": {"top": 25, "textStyle": {"fontSize": 10, "color": "#ccc"}, "type": "scroll"},
            "grid": {"left": 60, "right": 30, "top": 65, "bottom": 25},
            "xAxis": {
                "type": "category", "data": xd, "boundaryGap": False,
                "axisLabel": {"fontSize": 10},
                "axisPointer": {
                    "type": "line",
                    "lineStyle": {"color": "rgba(255,255,255,0.3)"},
                    "triggerTooltip": False,
                },
            },
            "yAxis": {"type": "value", "name": y_name,
                       "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.1)"}}},
            "series": series,
        }

        inits += f"""
        var {cid} = echarts.init(document.getElementById('{cid}'));
        {cid}.setOption({json.dumps(option, ensure_ascii=False)});
        """

    # crosshair 연동: hover 차트의 x 위치에 다른 차트는 세로선만 (tooltip 없이)
    sync_js = f"""
    var allCharts = [{','.join(chart_ids)}];
    allCharts.forEach(function(src, si) {{
        src.getZr().on('mousemove', function(e) {{
            var point = [e.offsetX, e.offsetY];
            if (!src.containPixel('grid', point)) return;
            var dataIndex = src.convertFromPixel({{seriesIndex: 0}}, point)[0];
            if (dataIndex == null || dataIndex < 0) return;
            allCharts.forEach(function(dst, di) {{
                if (di !== si) {{
                    var xAxis = dst.getModel().getComponent('xAxis', 0);
                    var data = xAxis.get('data');
                    if (dataIndex < data.length) {{
                        dst.setOption({{
                            xAxis: {{
                                axisPointer: {{
                                    value: data[dataIndex],
                                    status: 'show'
                                }}
                            }}
                        }});
                    }}
                }}
            }});
        }});
        src.getZr().on('globalout', function() {{
            allCharts.forEach(function(dst, di) {{
                if (di !== si) {{
                    dst.setOption({{
                        xAxis: {{
                            axisPointer: {{
                                status: 'hide'
                            }}
                        }}
                    }});
                }}
            }});
        }});
    }});
    """

    html = f"""
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
    </head>
    <body style="margin:0;padding:0;background:transparent;">
        {divs}
        <script>
            {inits}
            {sync_js}
            window.addEventListener('resize', function() {{
                {'; '.join([f'{c}.resize()' for c in chart_ids])};
            }});
        </script>
    </body>
    </html>
    """
    components.html(html, height=total_h + 20, scrolling=True)


phase_dir = RESULTS_DIR / scenario_info["phase"]
if not phase_dir.exists():
    st.warning(f"No results: {phase_dir}")
    st.info("Run: python scripts/run_benchmark.py phase1|phase2|all")
else:
    create_dashboard(scenario_info)
