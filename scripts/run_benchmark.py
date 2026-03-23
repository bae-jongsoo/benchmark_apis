#!/usr/bin/env python3
"""
벤치마크 자동화 스크립트

Usage:
    python scripts/run_benchmark.py phase1
    python scripts/run_benchmark.py phase2
    python scripts/run_benchmark.py all
"""
import os
import sys
import yaml
import json
import csv
import time
import shutil
import subprocess
import threading
import argparse
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
RESULTS_DIR = PROJECT_ROOT / "results"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def init_results_dir(phase: str):
    """results/<phase>/ 전체 삭제 후 재생성"""
    phase_dir = RESULTS_DIR / phase
    if phase_dir.exists():
        shutil.rmtree(phase_dir)
    (phase_dir / "raw").mkdir(parents=True, exist_ok=True)


def get_server_config(config: dict, name: str) -> dict:
    """config.yaml에서 서버 구성을 이름으로 찾기"""
    for sc in config["server_configs"]:
        if sc["name"] == name:
            return sc
    raise ValueError(f"서버 구성을 찾을 수 없음: {name}")


def start_app_container(server_config: dict):
    """Docker Compose로 앱 컨테이너 기동"""
    framework = server_config["framework"]  # "django" or "fastapi"
    service = "django_app" if framework == "django" else "fastapi_app"

    env = os.environ.copy()
    env["WORKERS"] = str(server_config["workers"])
    env["APP_PORT"] = str(server_config["port"])
    if "cpu_handler" in server_config:
        env["CPU_HANDLER"] = server_config["cpu_handler"]

    subprocess.run(
        ["docker", "compose", "up", "-d", "--build", service],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
    )


def wait_for_health(port: int, timeout: int = 60):
    """서버가 응답할 때까지 대기"""
    url = f"http://localhost:{port}/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(1)
    raise TimeoutError(f"서버가 {timeout}초 내에 응답하지 않음: {url}")


def warmup(port: int, endpoint: str, seconds: int = 5):
    """워밍업 요청"""
    url = f"http://localhost:{port}{endpoint}"
    end_time = time.time() + seconds
    while time.time() < end_time:
        try:
            urllib.request.urlopen(url, timeout=5)
        except Exception:
            pass
        time.sleep(0.1)


def collect_docker_stats(
    container_name: str,
    output_csv: Path,
    stop_event: threading.Event,
    epoch_start: float,
    db_container: str | None = None,
    db_output_csv: Path | None = None,
):
    """1초 간격으로 docker stats API를 호출하여 CSV에 기록"""
    # CSV 헤더: elapsed_seconds, cpu_percent, memory_mb
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["elapsed_seconds", "cpu_percent", "memory_mb"])

    # DB stats CSV (Phase 2)
    if db_container and db_output_csv:
        with open(db_output_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["elapsed_seconds", "cpu_percent", "memory_mb"])

    while not stop_event.is_set():
        elapsed = time.time() - epoch_start

        # 앱 컨테이너 stats
        stats = _get_container_stats(container_name)
        if stats:
            with open(output_csv, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    f"{elapsed:.1f}",
                    f"{stats['cpu_percent']:.2f}",
                    f"{stats['memory_mb']:.2f}",
                ])

        # DB 컨테이너 stats (Phase 2)
        if db_container and db_output_csv:
            db_stats = _get_container_stats(db_container)
            if db_stats:
                with open(db_output_csv, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        f"{elapsed:.1f}",
                        f"{db_stats['cpu_percent']:.2f}",
                        f"{db_stats['memory_mb']:.2f}",
                    ])

        stop_event.wait(1.0)  # 1초 간격


def _get_container_stats(container_name: str) -> dict | None:
    """docker stats --no-stream으로 CPU%, Memory 가져오기"""
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format",
             "{{.CPUPerc}}\t{{.MemUsage}}", container_name],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        line = result.stdout.strip()
        if not line:
            return None
        parts = line.split("\t")
        cpu_str = parts[0].replace("%", "")
        mem_str = parts[1].split("/")[0].strip()
        # 메모리 단위 변환 (MiB, GiB → MB)
        memory_mb = _parse_memory(mem_str)
        return {"cpu_percent": float(cpu_str), "memory_mb": memory_mb}
    except Exception:
        return None


def _parse_memory(mem_str: str) -> float:
    """Docker stats 메모리 문자열을 MB로 변환"""
    mem_str = mem_str.strip()
    if mem_str.endswith("GiB"):
        return float(mem_str[:-3]) * 1024
    elif mem_str.endswith("MiB"):
        return float(mem_str[:-3])
    elif mem_str.endswith("KiB"):
        return float(mem_str[:-3]) / 1024
    elif mem_str.endswith("B"):
        return float(mem_str[:-1]) / (1024 * 1024)
    return 0.0


def _get_container_id(service_name: str) -> str:
    """docker compose ps로 서비스의 컨테이너 ID를 동적으로 가져오기"""
    result = subprocess.run(
        ["docker", "compose", "ps", "-q", service_name],
        cwd=PROJECT_ROOT,
        capture_output=True, text=True,
    )
    container_id = result.stdout.strip()
    if not container_id:
        raise RuntimeError(f"컨테이너를 찾을 수 없음: {service_name}")
    return container_id


def check_db_seed():
    """my-postgres 컨테이너가 실행 중이고 foods 테이블에 데이터가 있는지 확인"""
    # 1. my-postgres 컨테이너 실행 확인
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", "my-postgres"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or result.stdout.strip() != "true":
        print("ERROR: my-postgres 컨테이너가 실행 중이지 않습니다.")
        print("  → docker start my-postgres")
        sys.exit(1)

    # 2. foods 테이블 데이터 존재 확인
    result = subprocess.run(
        ["docker", "exec", "my-postgres",
         "psql", "-U", "postgres", "-d", "foodcommit", "-t", "-c",
         "SELECT COUNT(*) FROM foods;"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("ERROR: foods 테이블을 조회할 수 없습니다.")
        print("  → Django 마이그레이션과 시드를 먼저 실행하세요:")
        print("  → python django_app/seed.py")
        sys.exit(1)

    count = int(result.stdout.strip())
    if count == 0:
        print("ERROR: foods 테이블에 데이터가 없습니다.")
        print("  → python django_app/seed.py")
        sys.exit(1)

    print(f"DB 시드 확인 완료: {count}건")


def run_k6(
    scenario: str,
    config_name: str,
    port: int,
    phase: str,
):
    """k6 Docker 컨테이너로 테스트 실행"""
    raw_json_path = f"/results/{phase}/raw/{scenario}_{config_name}.json"

    subprocess.run(
        [
            "docker", "compose", "run", "--rm",
            "-e", f"BASE_URL=http://host.docker.internal:{port}",
            "k6", "run",
            "--out", f"json={raw_json_path}",
            f"/scripts/{scenario}.js",
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )


def stop_app_container(framework: str):
    """앱 컨테이너 종료"""
    service = "django_app" if framework == "django" else "fastapi_app"
    subprocess.run(
        ["docker", "compose", "stop", service],
        cwd=PROJECT_ROOT,
    )
    subprocess.run(
        ["docker", "compose", "rm", "-f", service],
        cwd=PROJECT_ROOT,
    )


def postprocess_k6_json(raw_json_path: Path, output_csv_path: Path):
    """
    k6 JSON 출력을 파싱하여 1초 단위 집계 CSV 생성

    k6 JSON 형식: 각 줄이 JSON 오브젝트
    - type: "Point" → metric data point
    - metric: "http_req_duration" → 응답 시간 (ms)
    - data.time: ISO timestamp
    - data.value: metric value

    출력 CSV 컬럼:
    - elapsed_seconds: 테스트 시작부터의 경과 시간 (0, 1, 2, ...)
    - rps: 해당 초의 요청 수
    - latency_p50: 응답 시간 P50 (ms)
    - latency_p95: 응답 시간 P95 (ms)
    - latency_p99: 응답 시간 P99 (ms)
    - error_rate: 에러율 (%)
    """
    # k6 JSON 파싱
    durations = {}    # {second: [duration_ms, ...]}
    failures = {}     # {second: [0 or 1, ...]}  — http_req_failed 메트릭
    min_time = None

    with open(raw_json_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if obj.get("type") != "Point":
                continue

            metric = obj.get("metric")
            timestamp = obj["data"]["time"]
            value = obj["data"]["value"]

            # ISO timestamp → epoch seconds
            ts = _parse_k6_timestamp(timestamp)

            if min_time is None:
                min_time = ts

            elapsed_sec = int(ts - min_time)

            if metric == "http_req_duration":
                durations.setdefault(elapsed_sec, []).append(value)
            elif metric == "http_req_failed":
                # k6 built-in 메트릭: value=0(성공), value=1(실패)
                failures.setdefault(elapsed_sec, []).append(int(value))

    if not durations:
        return

    # 1초 단위 집계
    max_sec = max(durations.keys())
    with open(output_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["elapsed_seconds", "rps", "latency_p50", "latency_p95", "latency_p99", "error_rate"])

        for sec in range(max_sec + 1):
            durs = sorted(durations.get(sec, []))
            fails = failures.get(sec, [])

            if not durs:
                writer.writerow([sec, 0, 0, 0, 0, 0])
                continue

            rps = len(durs)
            p50 = _percentile(durs, 50)
            p95 = _percentile(durs, 95)
            p99 = _percentile(durs, 99)

            # 에러율: http_req_failed 메트릭 (value=1이 에러)
            if fails:
                error_count = sum(fails)
                error_rate = (error_count / len(fails)) * 100
            else:
                error_rate = 0.0

            writer.writerow([
                sec,
                rps,
                f"{p50:.2f}",
                f"{p95:.2f}",
                f"{p99:.2f}",
                f"{error_rate:.2f}",
            ])


def _parse_k6_timestamp(ts_str: str) -> float:
    """k6 JSON timestamp → epoch seconds"""
    # 형식: "2024-01-01T00:00:00.000000Z" 또는 유사
    # fromisoformat은 'Z' 접미사를 처리하지 못할 수 있으므로 변환
    ts_str = ts_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(ts_str)
    return dt.timestamp()


def _percentile(sorted_list: list, pct: int) -> float:
    """정렬된 리스트에서 백분위 계산"""
    if not sorted_list:
        return 0.0
    idx = int(len(sorted_list) * pct / 100)
    idx = min(idx, len(sorted_list) - 1)
    return sorted_list[idx]


def run_phase(phase: str, config: dict):
    """Phase 실행"""
    scenarios = config.get(f"{phase}_scenarios", {})
    test_duration = config.get("test_duration", 40)
    warmup_seconds = config.get("warmup_seconds", 5)

    init_results_dir(phase)

    # Phase 2: DB 시드 확인
    if phase == "phase2":
        check_db_seed()

    for scenario_name, config_names in scenarios.items():
        print(f"\n{'='*60}")
        print(f"시나리오: {scenario_name}")
        print(f"{'='*60}")

        for config_name in config_names:
            print(f"\n--- {config_name} ---")
            sc = get_server_config(config, config_name)

            # 1. 앱 컨테이너 기동
            start_app_container(sc)

            # 2. 헬스체크 대기
            wait_for_health(sc["port"])

            # 3. 워밍업 엔드포인트 결정
            warmup_endpoint = {
                "cpu_bound": "/benchmark/cpu",
                "io_bound": "/benchmark/io",
                "mixed": "/benchmark/mixed",
                "real_simple": "/api/foods?page=1&size=20",
                "real_heavy": "/api/foods/search?min_energy=100&max_energy=500&page=1&size=20",
            }.get(scenario_name, "/benchmark/cpu")

            warmup(sc["port"], warmup_endpoint, warmup_seconds)

            # 4. docker stats 수집 시작 (별도 스레드)
            epoch_start = time.time()
            stop_event = threading.Event()

            stats_csv = RESULTS_DIR / phase / f"stats_{scenario_name}_{config_name}.csv"

            # Phase 2: DB 컨테이너 모니터링
            db_container = None
            db_stats_csv = None
            if phase == "phase2":
                db_container = "my-postgres"
                db_stats_csv = RESULTS_DIR / phase / f"stats_db_{scenario_name}_{config_name}.csv"

            # 앱 컨테이너 ID를 동적으로 가져오기 (프로젝트명에 의존하지 않음)
            framework = sc["framework"]
            service_name = "django_app" if framework == "django" else "fastapi_app"
            app_container = _get_container_id(service_name)

            stats_thread = threading.Thread(
                target=collect_docker_stats,
                args=(app_container, stats_csv, stop_event, epoch_start,
                      db_container, db_stats_csv),
            )
            stats_thread.start()

            # 5. k6 실행
            try:
                run_k6(scenario_name, config_name, sc["port"], phase)
            finally:
                # 6. stats 수집 종료
                stop_event.set()
                stats_thread.join()

                # 7. 앱 컨테이너 종료
                stop_app_container(sc["framework"])

    # 8. 후처리: raw JSON → 집계 CSV
    print(f"\n후처리 시작: {phase}")
    raw_dir = RESULTS_DIR / phase / "raw"
    for json_file in raw_dir.glob("*.json"):
        csv_name = json_file.stem + ".csv"
        csv_path = RESULTS_DIR / phase / csv_name
        postprocess_k6_json(json_file, csv_path)
        print(f"  {json_file.name} → {csv_name}")


def main():
    parser = argparse.ArgumentParser(description="벤치마크 자동화")
    parser.add_argument("phase", choices=["phase1", "phase2", "all"])
    args = parser.parse_args()

    config = load_config()

    if args.phase in ("phase1", "all"):
        run_phase("phase1", config)
    if args.phase in ("phase2", "all"):
        run_phase("phase2", config)

    print("\n벤치마크 완료!")


if __name__ == "__main__":
    main()
