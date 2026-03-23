# 07. Streamlit 대시보드

## 목표
벤치마크 결과 CSV를 읽어 Plotly 기반 인터랙티브 차트로 시각화하는 Streamlit 웹앱을 구현한다. Phase 1과 Phase 2 결과를 통합하여 사이드바에서 시나리오를 선택하면 해당 차트들이 세로로 배치된다.

## 선행 태스크
- 01-project-setup (프로젝트 구조)
- 06-benchmark-automation (결과 CSV 포맷 확인)

## 구현할 파일 목록

### 1. `requirements.txt` (프로젝트 루트) — 대시보드 의존성

```
streamlit>=1.28
plotly>=5.18
pandas>=2.0
pyyaml>=6.0
```

### 2. `dashboard.py` — Streamlit 대시보드 메인

#### 전체 구조

```python
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import yaml

RESULTS_DIR = Path("results")
CONFIG_PATH = Path("config.yaml")

# 색상 스키마: Django=녹색 톤, FastAPI=파란색 톤
COLORS = {
    "django-4w": "#2ecc71",       # 녹색
    "django-32w": "#27ae60",      # 진한 녹색
    "fastapi-2w": "#3498db",      # 파란색
    "fastapi-4w": "#2980b9",      # 진한 파란색
    "fastapi-4w-sync": "#1abc9c", # 청록색
    "fastapi-4w-async": "#e74c3c",# 빨간색 (이벤트루프 블로킹 — 구분 용이하게)
}
```

#### 사이드바 — 시나리오 선택

```python
st.set_page_config(page_title="Django vs FastAPI Benchmark", layout="wide")
st.title("Django Ninja vs FastAPI 벤치마크 대시보드")

# config.yaml에서 시나리오 목록 로드
config = yaml.safe_load(open(CONFIG_PATH))

# 시나리오 목록 구성
scenarios = {}
for scenario_name, configs in config.get("phase1_scenarios", {}).items():
    scenarios[f"Phase 1: {scenario_name}"] = {
        "phase": "phase1",
        "scenario": scenario_name,
        "configs": configs,
        "has_db_stats": False,
    }
for scenario_name, configs in config.get("phase2_scenarios", {}).items():
    scenarios[f"Phase 2: {scenario_name}"] = {
        "phase": "phase2",
        "scenario": scenario_name,
        "configs": configs,
        "has_db_stats": True,
    }

selected = st.sidebar.selectbox("시나리오 선택", list(scenarios.keys()))
scenario_info = scenarios[selected]
```

#### CSV 로드

```python
def load_k6_csv(phase: str, scenario: str, config_name: str) -> pd.DataFrame | None:
    """1초 단위 집계 CSV 로드"""
    csv_path = RESULTS_DIR / phase / f"{scenario}_{config_name}.csv"
    if not csv_path.exists():
        return None
    return pd.read_csv(csv_path)


def load_stats_csv(phase: str, scenario: str, config_name: str) -> pd.DataFrame | None:
    """docker stats CSV 로드"""
    csv_path = RESULTS_DIR / phase / f"stats_{scenario}_{config_name}.csv"
    if not csv_path.exists():
        return None
    return pd.read_csv(csv_path)


def load_db_stats_csv(phase: str, scenario: str, config_name: str) -> pd.DataFrame | None:
    """DB docker stats CSV 로드 (Phase 2만)"""
    csv_path = RESULTS_DIR / phase / f"stats_db_{scenario}_{config_name}.csv"
    if not csv_path.exists():
        return None
    return pd.read_csv(csv_path)
```

#### 차트 생성

각 차트는 Plotly `go.Figure`로 생성하며, `shared_xaxes` 기능을 위해 서브플롯이 아닌 개별 차트를 세로로 배치한다. 단, X축 범위를 공유하기 위해 Plotly의 `rangeslider`와 `relayoutData` 이벤트를 활용할 수 있다.

**Streamlit에서 `shared_xaxes` 구현**: Plotly subplots를 사용하여 모든 차트를 하나의 Figure에 배치하면 드래그 줌 시 동시에 줌인된다.

```python
def create_dashboard(scenario_info: dict):
    phase = scenario_info["phase"]
    scenario = scenario_info["scenario"]
    configs = scenario_info["configs"]
    has_db_stats = scenario_info["has_db_stats"]

    # 차트 수 결정
    n_charts = 7 if has_db_stats else 5
    subplot_titles = ["RPS (Requests Per Second)", "Latency (ms)", "Error Rate (%)",
                      "CPU Usage (%)", "Memory Usage (MB)"]
    if has_db_stats:
        subplot_titles += ["DB CPU Usage (%)", "DB Memory Usage (MB)"]

    fig = make_subplots(
        rows=n_charts, cols=1,
        shared_xaxes=True,
        subplot_titles=subplot_titles,
        vertical_spacing=0.04,
    )

    for config_name in configs:
        color = COLORS.get(config_name, "#95a5a6")

        # k6 집계 CSV
        k6_df = load_k6_csv(phase, scenario, config_name)
        if k6_df is not None:
            x = k6_df["elapsed_seconds"]

            # 1. RPS
            fig.add_trace(
                go.Scatter(x=x, y=k6_df["rps"], name=config_name,
                          line=dict(color=color), legendgroup=config_name,
                          showlegend=True),
                row=1, col=1,
            )

            # 2. Latency (P50, P95, P99)
            # 첫 번째 config에 대해서만 P50/P95/P99 범례를 표시하여 선 스타일 구분을 알려줌
            is_first_config = (config_name == configs[0])
            fig.add_trace(
                go.Scatter(x=x, y=k6_df["latency_p50"],
                          name=f"{config_name} P50",
                          line=dict(color=color, dash="solid"),
                          legendgroup=f"latency-{config_name}",
                          showlegend=is_first_config),
                row=2, col=1,
            )
            fig.add_trace(
                go.Scatter(x=x, y=k6_df["latency_p95"],
                          name=f"{config_name} P95",
                          line=dict(color=color, dash="dash"),
                          legendgroup=f"latency-{config_name}",
                          showlegend=is_first_config),
                row=2, col=1,
            )
            fig.add_trace(
                go.Scatter(x=x, y=k6_df["latency_p99"],
                          name=f"{config_name} P99",
                          line=dict(color=color, dash="dot"),
                          legendgroup=f"latency-{config_name}",
                          showlegend=is_first_config),
                row=2, col=1,
            )

            # 3. Error Rate
            fig.add_trace(
                go.Scatter(x=x, y=k6_df["error_rate"], name=config_name,
                          line=dict(color=color), legendgroup=config_name,
                          showlegend=False),
                row=3, col=1,
            )

        # docker stats CSV
        stats_df = load_stats_csv(phase, scenario, config_name)
        if stats_df is not None:
            sx = stats_df["elapsed_seconds"]

            # 4. CPU Usage
            fig.add_trace(
                go.Scatter(x=sx, y=stats_df["cpu_percent"], name=config_name,
                          line=dict(color=color), legendgroup=config_name,
                          showlegend=False),
                row=4, col=1,
            )

            # 5. Memory Usage
            fig.add_trace(
                go.Scatter(x=sx, y=stats_df["memory_mb"], name=config_name,
                          line=dict(color=color), legendgroup=config_name,
                          showlegend=False),
                row=5, col=1,
            )

        # Phase 2: DB stats
        if has_db_stats:
            db_df = load_db_stats_csv(phase, scenario, config_name)
            if db_df is not None:
                dx = db_df["elapsed_seconds"]

                # 6. DB CPU Usage
                fig.add_trace(
                    go.Scatter(x=dx, y=db_df["cpu_percent"], name=config_name,
                              line=dict(color=color), legendgroup=config_name,
                              showlegend=False),
                    row=6, col=1,
                )

                # 7. DB Memory Usage
                fig.add_trace(
                    go.Scatter(x=dx, y=db_df["memory_mb"], name=config_name,
                              line=dict(color=color), legendgroup=config_name,
                              showlegend=False),
                    row=7, col=1,
                )

    # 레이아웃 설정
    fig.update_layout(
        height=300 * n_charts,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # X축 라벨 (마지막 차트만)
    fig.update_xaxes(title_text="Elapsed Time (seconds)", row=n_charts, col=1)

    # Y축 라벨
    y_labels = ["RPS", "Latency (ms)", "Error Rate (%)", "CPU (%)", "Memory (MB)"]
    if has_db_stats:
        y_labels += ["DB CPU (%)", "DB Memory (MB)"]
    for i, label in enumerate(y_labels, 1):
        fig.update_yaxes(title_text=label, row=i, col=1)

    st.plotly_chart(fig, use_container_width=True)
```

#### 메인 실행

```python
# 결과 디렉토리 존재 확인
phase_dir = RESULTS_DIR / scenario_info["phase"]
if not phase_dir.exists():
    st.warning(f"결과 디렉토리가 없습니다: {phase_dir}")
    st.info("먼저 벤치마크를 실행하세요: python scripts/run_benchmark.py phase1|phase2|all")
else:
    create_dashboard(scenario_info)
```

### 실행 방법
```bash
streamlit run dashboard.py
```

## 차트 스펙 (기획서 Section 7)

### Phase 1 시나리오 — 5개 차트
1. **RPS** — 시계열 라인 차트 (초당 요청 수)
2. **Latency (P50, P95, P99)** — 시계열 라인 차트 (ms)
3. **Error Rate** — 시계열 라인 차트 (%)
4. **CPU Usage** — 시계열 라인 차트 (%)
5. **Memory Usage** — 시계열 라인 차트 (MB)

### Phase 2 시나리오 — 7개 차트
위 5개 + 추가 2개:
6. **DB CPU Usage** — 시계열 라인 차트 (%)
7. **DB Memory Usage** — 시계열 라인 차트 (MB)

### 스타일
- Django 계열: 녹색 톤 (`#2ecc71`, `#27ae60`)
- FastAPI 계열: 파란색 톤 (`#3498db`, `#2980b9`)
- `fastapi-4w-sync`: 청록색 (`#1abc9c`)
- `fastapi-4w-async`: 빨간색 (`#e74c3c`) — 이벤트 루프 블로킹이므로 시각적 구분
- Streamlit 기본 테마 사용 (다크/라이트 모드 자동 지원)
- Plotly `shared_xaxes`: 하나의 차트를 드래그 줌하면 나머지도 동시에 줌인
- X축: elapsed time (0초~40초) 정규화
- Latency 차트: P50=실선, P95=대시, P99=점선으로 구분

## 완료 기준
- `dashboard.py`가 존재하고 `streamlit run dashboard.py`로 실행된다
- 사이드바에서 시나리오(Phase 1: cpu_bound/io_bound/mixed, Phase 2: real_simple/real_heavy)를 선택할 수 있다
- 선택한 시나리오에 해당하는 서버 구성만 차트에 표시된다
- Phase 1: 5개 차트, Phase 2: 7개 차트가 세로로 배치된다
- Plotly `shared_xaxes`로 줌 동기화가 동작한다
- 결과가 없는 경우 안내 메시지를 표시한다
- Django=녹색, FastAPI=파란색 계열 색상이 적용된다
