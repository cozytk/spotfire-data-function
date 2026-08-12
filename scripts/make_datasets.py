"""교육용 합성 데이터 생성 스크립트.

data/ 폴더의 CSV 중 아래 파일들을 재현 가능한 난수(seed 고정)로 생성합니다.
  - fab_measurement.csv        : 공정 계측 이력 (중복/결측/이상치/드리프트 포함)
  - lot_master.csv             : LOT 마스터 (조인용)
  - equipment_sensor_wide.csv  : 설비 센서 wide 포맷 (melt 실습용)
  - equipment_alarm_log.csv    : 설비 알람 로그 (정규식 파싱/연속구간 실습용)
  - wafer_yield.csv            : 웨이퍼 수율/불량 유형 (파레토 실습용)
  - hr_training.csv            : 임직원 교육 이수 현황 (피벗/크로스탭 실습용)
  - sales_orders.csv           : 제품 수주/출하 (시계열/ABC 실습용)
  - diabetes_train.csv         : 공개 Pima 당뇨 데이터에 헤더를 붙여 저장

※ titanic.csv / iris.csv 는 공개 데이터를 그대로 사용합니다.
※ 사내 실제 데이터가 아니라 교육용으로 만든 가상의 데이터입니다.

실행: python scripts/make_datasets.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260312)
DATA = Path(__file__).resolve().parents[1] / "data"
DATA.mkdir(exist_ok=True)

STEPS = {
    "PC": "PC",
    "RMG": "RMG",
    "CBCMP": "CMP",
    "ETCH": "ETC",
    "PHOTO": "PHO",
}
PRODUCTS = ["D1Z-DDR5-16G", "D1B-DDR5-24G", "V8-NAND-1Tb", "V9-NAND-2Tb", "LSI-ISOCELL-HP2"]
LINES = ["P1", "P2", "P3", "H1"]


def _ts(start, periods, freq_min):
    return pd.date_range(start, periods=periods, freq=f"{freq_min}min")


# ---------------------------------------------------------------- lot_master
def make_lot_master(n_lot=120):
    lot_ids = [f"L{26000 + i:05d}" for i in range(n_lot)]
    start = pd.Timestamp("2026-03-02 06:00:00")
    df = pd.DataFrame(
        {
            "LOT_ID": lot_ids,
            "JOIN_ID": lot_ids,  # 기존 실습 스크립트와 동일한 조인 키 이름도 함께 제공
            "PRODUCT": RNG.choice(PRODUCTS, n_lot),
            "LINE": RNG.choice(LINES, n_lot),
            "PRIORITY": RNG.choice(["HOT", "NORMAL", "LOW"], n_lot, p=[0.15, 0.7, 0.15]),
            "PLAN_QTY": RNG.choice([25, 25, 25, 24, 12], n_lot),
            "START_TIME": [start + pd.Timedelta(minutes=int(m)) for m in RNG.integers(0, 7 * 24 * 60, n_lot)],
            "OWNER_DEPT": RNG.choice(
                ["메모리제조기술", "메모리공정개발", "파운드리제조", "시스템LSI개발", "품질보증"], n_lot
            ),
        }
    )
    df["START_TIME"] = df["START_TIME"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df.to_csv(DATA / "lot_master.csv", index=False, encoding="utf-8-sig")
    return df


# --------------------------------------------------------- fab_measurement
def make_fab_measurement(lot_master):
    rows = []
    base_time = pd.Timestamp("2026-03-02 06:00:00")
    for lot in lot_master["LOT_ID"]:
        n_wafer = int(RNG.choice([25, 25, 12]))
        for step_desc, eqp_prefix in STEPS.items():
            eqp_id = f"{eqp_prefix}{RNG.integers(1, 3):02d}"
            chamber = RNG.choice(["A", "B", "C"])
            step_t0 = base_time + pd.Timedelta(minutes=int(RNG.integers(0, 7 * 24 * 60)))
            # 설비/챔버별 공정 목표값과 드리프트
            thick_target = {"PC": 520.0, "RMG": 310.0, "CBCMP": 980.0, "ETCH": 145.0, "PHOTO": 88.0}[step_desc]
            drift = RNG.normal(0, 0.02) * thick_target
            for w in range(1, n_wafer + 1, int(RNG.choice([1, 1, 2]))):
                t = step_t0 + pd.Timedelta(minutes=float(w) * 1.7)
                pos = w / n_wafer
                thickness = thick_target + drift * pos + RNG.normal(0, thick_target * 0.008)
                cd = 32.0 + RNG.normal(0, 0.45) + (1.2 if eqp_id.endswith("02") else 0)
                temp = 235.0 + RNG.normal(0, 3.5)
                pressure = 12.0 + RNG.normal(0, 0.4)
                particle = max(0, int(RNG.poisson(4) + (12 if RNG.random() < 0.02 else 0)))
                rows.append(
                    {
                        "LOT_ID": lot,
                        "JOIN_ID": lot,
                        "WAFER_NO": w,
                        "STEP_DESC": step_desc,
                        "EQP_ID": eqp_id,
                        "CHAMBER": chamber,
                        "MEAS_TIME": t,
                        "THICKNESS": round(thickness, 3),
                        "CD": round(cd, 3),
                        "TEMP": round(temp, 2),
                        "PRESSURE": round(pressure, 3),
                        "PARTICLE_CNT": particle,
                        "SIZE_Y": round(abs(RNG.normal(1.2, 0.3)), 3),
                        "IS_DEFECT": RNG.choice(["REAL", "FALSE", "FALSE", "FALSE"], p=[0.08, 0.3, 0.31, 0.31]),
                        "OPER_ID": f"E{RNG.integers(100000, 999999)}",
                    }
                )
    df = pd.DataFrame(rows)

    # --- 일부러 심어 두는 '지저분함' -------------------------------------
    # 1) 이상치 스파이크 (설비 이상)
    idx = RNG.choice(df.index, size=int(len(df) * 0.012), replace=False)
    df.loc[idx, "THICKNESS"] = df.loc[idx, "THICKNESS"] * RNG.uniform(1.15, 1.4, len(idx))
    # 2) 결측치
    for col, ratio in [("CD", 0.04), ("TEMP", 0.03), ("THICKNESS", 0.02), ("SIZE_Y", 0.05)]:
        miss = RNG.choice(df.index, size=int(len(df) * ratio), replace=False)
        df.loc[miss, col] = np.nan
    # 3) 0 값(센서 미취득) — "0이 있는 행 지우기" 실습용
    zero = RNG.choice(df.index, size=int(len(df) * 0.015), replace=False)
    df.loc[zero, "PRESSURE"] = 0.0
    # 4) 완전 중복 행 (수집 시스템 재전송)
    dup = df.sample(frac=0.03, random_state=7).copy()
    # 5) 재측정 행 (같은 LOT/WAFER/STEP, 시각만 다름) — "최신값만 남기기" 실습용
    remeasure = df.sample(frac=0.02, random_state=11).copy()
    remeasure["MEAS_TIME"] = remeasure["MEAS_TIME"] + pd.Timedelta(minutes=45)
    remeasure["THICKNESS"] = remeasure["THICKNESS"] * RNG.uniform(0.98, 1.02, len(remeasure))
    df = pd.concat([df, dup, remeasure], ignore_index=True)
    df = df.sample(frac=1.0, random_state=3).sort_values("MEAS_TIME").reset_index(drop=True)
    df["MEAS_TIME"] = df["MEAS_TIME"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df.to_csv(DATA / "fab_measurement.csv", index=False, encoding="utf-8-sig")
    return df


# ---------------------------------------------------- equipment_sensor_wide
def make_sensor_wide():
    eqps = ["ETC01", "ETC02", "CMP01", "CMP02"]
    times = _ts("2026-03-02 06:00:00", 336, 30)  # 7일 × 30분 간격
    frames = []
    for eqp in eqps:
        base = RNG.normal(0, 1, 20) * 5 + 50
        vals = base + RNG.normal(0, 1.2, (len(times), 20)).cumsum(axis=0) * 0.05
        block = pd.DataFrame(vals.round(3), columns=[f"S{i:03d}" for i in range(1, 21)])
        block.insert(0, "EQP_ID", eqp)
        block.insert(0, "TIMESTAMP", times.strftime("%Y-%m-%d %H:%M:%S"))
        frames.append(block)
    df = pd.concat(frames, ignore_index=True)
    # 센서 결측 (통신 유실)
    for col in [c for c in df.columns if c.startswith("S")]:
        miss = RNG.choice(df.index, size=int(len(df) * 0.01), replace=False)
        df.loc[miss, col] = np.nan
    df.to_csv(DATA / "equipment_sensor_wide.csv", index=False, encoding="utf-8-sig")
    return df


# ---------------------------------------------------- equipment_alarm_log
def make_alarm_log(n=900):
    eqps = ["ETC01", "ETC02", "CMP01", "CMP02", "PHO01", "PC01"]
    codes = [
        ("E-1023", "Chamber pressure high", "ERROR"),
        ("E-2011", "RF power unstable", "ERROR"),
        ("W-3305", "Slurry flow low", "WARN"),
        ("W-3306", "Pad temperature drift", "WARN"),
        ("E-4102", "Wafer transfer timeout", "ERROR"),
        ("I-5000", "Recipe changed by operator", "INFO"),
    ]
    t = pd.Timestamp("2026-03-02 06:00:00")
    rows = []
    for _ in range(n):
        t = t + pd.Timedelta(minutes=float(RNG.exponential(11)))
        eqp = RNG.choice(eqps)
        code, msg, sev = codes[int(RNG.integers(0, len(codes)))]
        lot = f"L{26000 + RNG.integers(0, 120):05d}"
        step = str(RNG.choice(list(STEPS.keys())))
        value = round(float(RNG.uniform(0.5, 25)), 2)
        rows.append(
            {
                "EQP_ID": eqp,
                "ALARM_TIME": t.strftime("%Y-%m-%d %H:%M:%S"),
                "SEVERITY": sev,
                "MESSAGE": f"[{code}] {msg} (LOT={lot}, STEP={step}, value={value} unit)",
                "RECIPE": f"RCP_{step}_{RNG.integers(1, 6):02d}",
                "ACK_BY": RNG.choice(["", "", f"E{RNG.integers(100000, 999999)}"]),
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "equipment_alarm_log.csv", index=False, encoding="utf-8-sig")
    return df


# ------------------------------------------------------------- wafer_yield
def make_wafer_yield(lot_master):
    fail_types = [
        ("PARTICLE", 0.28),
        ("BRIDGE", 0.19),
        ("OPEN", 0.14),
        ("SCRATCH", 0.12),
        ("MISALIGN", 0.09),
        ("THIN_FILM", 0.07),
        ("EDGE_CHIP", 0.06),
        ("ETC", 0.05),
    ]
    names = [f[0] for f in fail_types]
    probs = np.array([f[1] for f in fail_types])
    probs = probs / probs.sum()
    rows = []
    for lot, prod, line in zip(lot_master["LOT_ID"], lot_master["PRODUCT"], lot_master["LINE"]):
        base_yield = float(RNG.normal(93, 3))
        for w in range(1, 26):
            total = 1200
            y = min(99.8, max(40.0, base_yield + RNG.normal(0, 1.8) - (6 if RNG.random() < 0.03 else 0)))
            good = int(total * y / 100)
            rows.append(
                {
                    "LOT_ID": lot,
                    "WAFER_NO": w,
                    "PRODUCT": prod,
                    "LINE": line,
                    "TOTAL_DIE": total,
                    "GOOD_DIE": good,
                    "YIELD_PCT": round(y, 2),
                    "MAIN_FAIL_TYPE": str(RNG.choice(names, p=probs)),
                    "TEST_DATE": (pd.Timestamp("2026-03-05") + pd.Timedelta(days=int(RNG.integers(0, 10)))).strftime(
                        "%Y-%m-%d"
                    ),
                }
            )
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "wafer_yield.csv", index=False, encoding="utf-8-sig")
    return df


# ------------------------------------------------------------- hr_training
def make_hr_training(n=1400):
    depts = ["메모리사업부", "시스템LSI사업부", "파운드리사업부", "반도체연구소", "글로벌인프라총괄", "DS경영지원"]
    roles = [
        "반도체공정기술", "설비기술", "회로설계", "평가및분석", "패키지개발",
        "S/W개발", "품질보증", "SCM/생산관리", "영업마케팅", "경영지원",
    ]
    courses = [
        ("Spotfire 기초", "데이터분석", 8),
        ("Spotfire 데이터함수(Python)", "데이터분석", 16),
        ("Python 기초", "데이터분석", 20),
        ("통계적공정관리(SPC)", "품질", 12),
        ("생성형 AI 활용", "AI", 6),
        ("반도체 8대 공정", "직무기초", 24),
        ("정보보호", "필수", 2),
    ]
    rows = []
    for i in range(n):
        c = courses[int(RNG.integers(0, len(courses)))]
        rows.append(
            {
                "EMP_ID": f"E{RNG.integers(100000, 999999)}",
                "DEPT": str(RNG.choice(depts)),
                "JOB_ROLE": str(RNG.choice(roles)),
                "GRADE": str(RNG.choice(["CL2", "CL3", "CL4"], p=[0.45, 0.4, 0.15])),
                "COURSE": c[0],
                "CATEGORY": c[1],
                "PLAN_HOURS": c[2],
                "DONE_HOURS": int(max(0, min(c[2], RNG.normal(c[2] * 0.8, c[2] * 0.25)))),
                "SCORE": np.nan if RNG.random() < 0.12 else int(RNG.normal(84, 9)),
                "COMPLETED_DATE": (
                    pd.Timestamp("2026-01-05") + pd.Timedelta(days=int(RNG.integers(0, 200)))
                ).strftime("%Y-%m-%d"),
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "hr_training.csv", index=False, encoding="utf-8-sig")
    return df


# ------------------------------------------------------------ sales_orders
def make_sales_orders(n=1600):
    customers = [f"CUST_{i:03d}" for i in range(1, 41)]
    regions = ["Korea", "China", "Taiwan", "USA", "Europe", "Japan"]
    rows = []
    for i in range(n):
        od = pd.Timestamp("2025-07-01") + pd.Timedelta(days=int(RNG.integers(0, 400)))
        qty = int(max(1, RNG.normal(2500, 1200)))
        price = round(float(RNG.uniform(1.8, 42.0)), 2)
        lead = int(max(1, RNG.normal(21, 9)))
        status = str(RNG.choice(["SHIPPED", "SHIPPED", "SHIPPED", "OPEN", "CANCELLED"], p=[0.6, 0.15, 0.15, 0.07, 0.03]))
        rows.append(
            {
                "ORDER_ID": f"SO{100000 + i}",
                "ORDER_DATE": od.strftime("%Y-%m-%d"),
                "CUSTOMER": str(RNG.choice(customers)),
                "REGION": str(RNG.choice(regions)),
                "PRODUCT_FAMILY": str(RNG.choice(PRODUCTS)),
                "QTY": qty,
                "UNIT_PRICE_USD": price,
                "AMOUNT_USD": round(qty * price, 2),
                "PROMISE_DATE": (od + pd.Timedelta(days=21)).strftime("%Y-%m-%d"),
                "SHIP_DATE": "" if status in ("OPEN", "CANCELLED") else (od + pd.Timedelta(days=lead)).strftime("%Y-%m-%d"),
                "STATUS": status,
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "sales_orders.csv", index=False, encoding="utf-8-sig")
    return df


# ------------------------------------------------------------ diabetes_train
def make_diabetes():
    raw = DATA / "_pima_raw.csv"
    if not raw.exists():
        return None
    cols = [
        "Pregnancies", "Glucose", "BloodPressure", "SkinThickness",
        "Insulin", "BMI", "DiabetesPedigreeFunction", "Age", "Outcome",
    ]
    df = pd.read_csv(raw, header=None, names=cols)
    train = df.sample(frac=0.8, random_state=42).sort_index()
    test = df.drop(train.index)
    train.to_csv(DATA / "diabetes_train.csv", index=False)
    test.to_csv(DATA / "diabetes_test.csv", index=False)
    raw.unlink()
    return train


if __name__ == "__main__":
    lot = make_lot_master()
    fab = make_fab_measurement(lot)
    sensor = make_sensor_wide()
    alarm = make_alarm_log()
    yld = make_wafer_yield(lot)
    hr = make_hr_training()
    sales = make_sales_orders()
    make_diabetes()
    for p in sorted(DATA.glob("*.csv")):
        n = sum(1 for _ in p.open(encoding="utf-8-sig")) - 1
        print(f"{p.name:32s} {n:7,d} rows  {p.stat().st_size / 1024:8.1f} KB")
