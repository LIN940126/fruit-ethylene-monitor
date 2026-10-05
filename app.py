from dash import Dash, html, dcc, Input, Output, State
import plotly.graph_objects as go
import random
import math
from datetime import datetime, timedelta


# =========================================================
# APP
# =========================================================

app = Dash(__name__)
app.title = "水果冷鏈乙烯智慧監測系統"


# =========================================================
# STYLE
# =========================================================

PAGE = {
    "fontFamily": "Arial, Microsoft JhengHei, sans-serif",
    "backgroundColor": "#f8fafc",
    "minHeight": "100vh",
    "padding": "30px",
    "color": "#0f172a",
}

CARD = {
    "backgroundColor": "white",
    "borderRadius": "16px",
    "padding": "22px",
    "boxShadow": "0 4px 15px rgba(0,0,0,0.06)",
    "border": "1px solid #e2e8f0",
}

METRIC = {
    "backgroundColor": "white",
    "borderRadius": "14px",
    "padding": "18px",
    "textAlign": "center",
    "boxShadow": "0 3px 12px rgba(0,0,0,0.05)",
    "border": "1px solid #e2e8f0",
}


# =========================================================
# PROTOTYPE 成熟判定門檻
# =========================================================
#
# 注意：
# 目前 3 ppm、6 ppm 僅為 Dashboard Prototype 示範門檻。
#
# 正式研究必須透過：
# 1. 感測器校正
# 2. 香蕉實際成熟實驗
# 3. 文獻
# 4. 統計分析
#
# 建立正式判定標準。
# =========================================================

RISK_THRESHOLD = 3.0
HIGH_RIPENESS_THRESHOLD = 6.0


# =========================================================
# 成熟階段
# =========================================================

def get_stage(value):

    if value >= HIGH_RIPENESS_THRESHOLD:
        return "高度成熟"

    elif value >= RISK_THRESHOLD:
        return "成熟風險上升"

    else:
        return "正常"


# =========================================================
# 建立 48 小時乙烯濃度歷史
# =========================================================

def create_history(final_value):

    now = datetime.now()

    times = [
        now - timedelta(hours=47 - i)
        for i in range(48)
    ]

    start_value = random.uniform(
        0.4,
        1.0
    )

    values = []

    for i in range(48):

        progress = i / 47

        # 模擬水果成熟後期乙烯增加較快
        curve = progress ** 1.45

        value = (
            start_value
            + (final_value - start_value)
            * curve
        )

        # 少量量測波動
        value += random.uniform(
            -0.12,
            0.12
        )

        values.append(
            round(
                max(0, value),
                2
            )
        )

    values[-1] = round(
        final_value,
        2
    )

    return times, values


# =========================================================
# EEI
# Ethylene Exposure Index
#
# 48 小時乙烯濃度曲線梯形積分
#
# 單位：
# ppm × hour = ppm·h
# =========================================================

def calculate_eei(values):

    eei = 0

    dt = 1.0

    for i in range(
        1,
        len(values)
    ):

        eei += (
            (
                values[i - 1]
                + values[i]
            )
            / 2
        ) * dt

    return round(
        eei,
        1
    )


# =========================================================
# dC/dt
#
# 使用最近 4 小時乙烯濃度變化估算
# =========================================================

def calculate_rate(values):

    if len(values) < 5:
        return 0

    delta_c = (
        values[-1]
        - values[-5]
    )

    delta_t = 4

    return round(
        delta_c / delta_t,
        2
    )


# =========================================================
# 尋找第一次超過成熟門檻的位置
# =========================================================

def find_threshold_index(
    values,
    threshold
):

    for i, value in enumerate(values):

        if value >= threshold:
            return i

    return None


# =========================================================
# RSSI 相對權重
#
# Prototype：
#
# -70 dBm → 接近 0
# -40 dBm → 接近 1
#
# 注意：
# 此處不是 RSSI → 實際距離公式。
# =========================================================

def rssi_weight(rssi):

    if rssi is None:
        return 0

    weight = (
        rssi + 70
    ) / 30

    return max(
        0,
        min(
            1,
            weight
        )
    )


# =========================================================
# NREI
# Neighbor Ripening Exposure Index
#
# Prototype：
#
# NREI = RSSI 相對權重 × 警示持續時間
#
# 此指標為目前研究構想，
# 不是既有標準。
# =========================================================

def calculate_nrei(
    rssi,
    exposure_hours
):

    if (
        rssi is None
        or exposure_hours is None
    ):
        return 0

    value = (
        rssi_weight(rssi)
        * exposure_hours
    )

    return round(
        value,
        1
    )


# =========================================================
# 產生模擬水果批次
# =========================================================

def generate_batch():

    tag_count = random.randint(
        8,
        14
    )

    tag_ids = sorted(
        random.sample(
            [
                f"A{i:02d}"
                for i in range(1, 60)
            ],
            tag_count
        )
    )

    tags = []

    # =====================================================
    # 建立每顆 Tag
    # =====================================================

    for tag_id in tag_ids:

        category = random.choices(
            [
                "normal",
                "risk",
                "high"
            ],
            weights=[
                0.50,
                0.30,
                0.20
            ]
        )[0]

        if category == "normal":

            final_value = random.uniform(
                0.7,
                2.8
            )

        elif category == "risk":

            final_value = random.uniform(
                3.0,
                5.8
            )

        else:

            final_value = random.uniform(
                6.2,
                9.5
            )

        times, values = create_history(
            final_value
        )

        current = values[-1]

        eei = calculate_eei(
            values
        )

        rate = calculate_rate(
            values
        )

        stage = get_stage(
            current
        )

        tags.append({

            "id": tag_id,

            "ethylene": current,

            "eei": eei,

            "rate": rate,

            "stage": stage,

            "times": [
                t.isoformat()
                for t in times
            ],

            "values": values,

            # Neighbor Alert
            "source": None,

            "rssi": None,

            "alert_index": None,

            "alert_time": None,

            "exposure_hours": 0,

            "nrei": 0,
        })

    # =====================================================
    # 保證至少有一個高度成熟 Tag
    # =====================================================

    high_tags = [
        tag
        for tag in tags
        if tag["stage"] == "高度成熟"
    ]

    if not high_tags:

        chosen = random.choice(
            tags
        )

        final_value = random.uniform(
            6.5,
            9.0
        )

        times, values = create_history(
            final_value
        )

        chosen["ethylene"] = (
            values[-1]
        )

        chosen["eei"] = (
            calculate_eei(
                values
            )
        )

        chosen["rate"] = (
            calculate_rate(
                values
            )
        )

        chosen["stage"] = (
            "高度成熟"
        )

        chosen["times"] = [
            t.isoformat()
            for t in times
        ]

        chosen["values"] = values

    # =====================================================
    # 找高度成熟來源
    # =====================================================

    high_tags = [
        tag
        for tag in tags
        if tag["stage"] == "高度成熟"
    ]

    # 最多使用兩個成熟警示來源
    if len(high_tags) > 2:

        alert_sources = random.sample(
            high_tags,
            2
        )

    else:

        alert_sources = high_tags

    # =====================================================
    # 模擬 Neighbor Alert
    # =====================================================

    for source in alert_sources:

        candidates = [
            tag
            for tag in tags
            if tag["id"] != source["id"]
        ]

        if not candidates:
            continue

        receiver_count = min(
            random.randint(
                2,
                4
            ),
            len(candidates)
        )

        receivers = random.sample(
            candidates,
            receiver_count
        )

        for receiver in receivers:

            rssi = random.randint(
                -67,
                -43
            )

            # 若同一 Tag 收到多個來源
            # 目前保留 RSSI 較強的主要來源
            if (
                receiver["rssi"] is None
                or rssi > receiver["rssi"]
            ):

                hours_ago = random.randint(
                    6,
                    30
                )

                alert_index = max(
                    0,
                    47 - hours_ago
                )

                receiver["source"] = (
                    source["id"]
                )

                receiver["rssi"] = rssi

                receiver[
                    "alert_index"
                ] = alert_index

                receiver[
                    "alert_time"
                ] = (
                    receiver["times"][
                        alert_index
                    ]
                )

                receiver[
                    "exposure_hours"
                ] = hours_ago

                receiver["nrei"] = (
                    calculate_nrei(
                        rssi,
                        hours_ago
                    )
                )

    # =====================================================
    # Batch
    # =====================================================

    now = datetime.now()

    batch_id = (
        "BANANA-"
        + now.strftime(
            "%Y%m%d-%H%M%S"
        )
    )

    return {

        "batch_id": batch_id,

        "time": now.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "tags": tags,

        "alert_sources": [
            tag["id"]
            for tag in alert_sources
        ]
    }


# =========================================================
# Neighbor Alert Network
#
# 注意：
# 此圖代表「警示通訊關聯」
# 不是實際水果空間位置。
# =========================================================

# =========================================================
# Neighbor Alert Network
#
# 樹狀排列：
# 上方 = 接收到成熟警示的 Tag
# 下方 = 高度成熟警示來源
#
# 注意：
# 此圖表示「無線警示通訊關聯」
# 不代表實際空間位置、距離或因果關係。
# =========================================================

def create_network(batch):

    tags = batch["tags"]

    source_ids = batch["alert_sources"]

    # =====================================================
    # 找出有收到 Neighbor Alert 的 Tag
    # =====================================================

    alert_tags = [
        tag
        for tag in tags
        if tag["source"] is not None
    ]

    # =====================================================
    # 依照成熟來源分組
    # =====================================================

    groups = {
        source: []
        for source in source_ids
    }

    for tag in alert_tags:

        if tag["source"] in groups:

            groups[tag["source"]].append(tag)

    # =====================================================
    # 建立圖
    # =====================================================

    fig = go.Figure()

    # 不同成熟來源群組之間的距離
    group_spacing = 8.0

    # =====================================================
    # 每一個成熟來源建立一組樹狀圖
    # =====================================================

    for group_index, source_id in enumerate(source_ids):

        receivers = groups.get(
            source_id,
            []
        )

        # -------------------------------------------------
        # 每個 Source 群組的中心位置
        # -------------------------------------------------

        center_x = (
            group_index
            - (len(source_ids) - 1) / 2
        ) * group_spacing

        # Source 放下面
        source_y = 0

        # Receiver 放上面
        receiver_y = 3.2

        # -------------------------------------------------
        # 找 Source 資料
        # -------------------------------------------------

        source_data = next(
            (
                tag
                for tag in tags
                if tag["id"] == source_id
            ),
            None
        )

        if source_data is None:
            continue

        # =================================================
        # 計算 Receiver 水平位置
        # =================================================

        receiver_positions = []

        count = len(receivers)

        if count == 1:

            receiver_positions = [
                center_x
            ]

        elif count > 1:

            # 每個 Receiver 間隔
            spacing = 2.0

            start_x = (
                center_x
                - ((count - 1) * spacing / 2)
            )

            receiver_positions = [
                start_x + i * spacing
                for i in range(count)
            ]

        # =================================================
        # 先畫連線
        # =================================================

        for receiver, receiver_x in zip(
            receivers,
            receiver_positions
        ):

            fig.add_trace(

                go.Scatter(

                    x=[
                        center_x,
                        receiver_x
                    ],

                    y=[
                        source_y,
                        receiver_y
                    ],

                    mode="lines",

                    line=dict(
                        width=2,
                        color="#f59e0b"
                    ),

                    hoverinfo="skip",

                    showlegend=False
                )
            )

        # =================================================
        # 畫成熟來源 Source
        # =================================================

        fig.add_trace(

            go.Scatter(

                x=[
                    center_x
                ],

                y=[
                    source_y
                ],

                mode="markers+text",

                text=[
                    source_id
                ],

                textposition="bottom center",

                textfont=dict(
                    size=14,
                    color="#334155"
                ),

                marker=dict(

                    size=40,

                    color="#ef4444",

                    line=dict(
                        width=3,
                        color="white"
                    )
                ),

                hovertemplate=(

                    f"<b>{source_id}</b><br>"
                    "角色：成熟警示來源<br>"
                    "自身狀態：高度成熟<br>"
                    f"C₂H₄："
                    f"{source_data['ethylene']} ppm<br>"
                    f"48h EEI："
                    f"{source_data['eei']} ppm·h<br>"
                    f"dC/dt："
                    f"{source_data['rate']:+.2f} ppm/h"

                    "<extra></extra>"
                ),

                showlegend=False
            )
        )

        # =================================================
        # 畫 Receiver
        # =================================================

        for receiver, receiver_x in zip(
            receivers,
            receiver_positions
        ):

            fig.add_trace(

                go.Scatter(

                    x=[
                        receiver_x
                    ],

                    y=[
                        receiver_y
                    ],

                    mode="markers+text",

                    text=[
                        receiver["id"]
                    ],

                    textposition="top center",

                    textfont=dict(
                        size=13,
                        color="#334155"
                    ),

                    marker=dict(

                        size=28,

                        color="#f59e0b",

                        line=dict(
                            width=2,
                            color="white"
                        )
                    ),

                    hovertemplate=(

                        f"<b>{receiver['id']}</b><br>"
                        f"警示來源："
                        f"{source_id}<br>"
                        f"自身成熟狀態："
                        f"{receiver['stage']}<br>"
                        f"C₂H₄："
                        f"{receiver['ethylene']} ppm<br>"
                        f"RSSI：約 "
                        f"{receiver['rssi']} dBm<br>"
                        f"警示紀錄時間："
                        f"{receiver['exposure_hours']} h<br>"
                        f"NREI："
                        f"{receiver['nrei']}"

                        "<extra></extra>"
                    ),

                    showlegend=False
                )
            )

    # =====================================================
    # 如果沒有 Neighbor Alert
    # =====================================================

    if len(source_ids) == 0:

        fig.add_annotation(

            x=0.5,
            y=0.5,

            xref="paper",
            yref="paper",

            text="目前沒有鄰近成熟警示紀錄",

            showarrow=False,

            font=dict(
                size=16,
                color="#64748b"
            )
        )

    # =====================================================
    # Layout
    # =====================================================

    fig.update_layout(

        title={

            "text": (
                "Neighbor Alert Network｜"
                "鄰近成熟警示通訊關聯"
            ),

            "x": 0.03
        },

        plot_bgcolor="white",

        paper_bgcolor="white",

        showlegend=False,

        height=430,

        margin=dict(
            l=50,
            r=50,
            t=75,
            b=80
        ),

        xaxis=dict(

            visible=False,

            showgrid=False,

            zeroline=False
        ),

        yaxis=dict(

            visible=False,

            showgrid=False,

            zeroline=False,

            range=[
                -1.1,
                4.2
            ]
        ),

        hoverlabel=dict(

            bgcolor="white",

            font_size=13
        )
    )

    # =====================================================
    # 簡單圖例
    # =====================================================

    fig.add_annotation(

        x=0.5,

        y=-0.08,

        xref="paper",

        yref="paper",

        text=(
            "🔴 高度成熟警示來源　　"
            "🟡 警示接收節點"
        ),

        showarrow=False,

        font=dict(
            size=12,
            color="#64748b"
        )
    )

    return fig


# =========================================================
# 建立 48h 成熟階段曲線
# =========================================================

def create_history_figure(tag):

    times = [
        datetime.fromisoformat(t)
        for t in tag["times"]
    ]

    values = tag["values"]

    # =====================================================
    # 找藍 → 黃
    # =====================================================

    risk_index = find_threshold_index(
        values,
        RISK_THRESHOLD
    )

    # =====================================================
    # 找黃 → 紅
    # =====================================================

    high_index = find_threshold_index(
        values,
        HIGH_RIPENESS_THRESHOLD
    )

    fig = go.Figure()

    # =====================================================
    # BLUE：正常
    # =====================================================

    blue_end = (
        risk_index
        if risk_index is not None
        else len(values) - 1
    )

    fig.add_trace(

        go.Scatter(

            x=times[
                :blue_end + 1
            ],

            y=values[
                :blue_end + 1
            ],

            mode="lines+markers",

            name="正常",

            line=dict(
                width=3,
                color="#3b82f6"
            ),

            marker=dict(
                size=5,
                color="#3b82f6"
            ),

            hovertemplate=(
                "%{x|%Y-%m-%d %H:%M}<br>"
                "C₂H₄：%{y:.2f} ppm<br>"
                "成熟階段：正常"
                "<extra></extra>"
            )
        )
    )

    # =====================================================
    # YELLOW：成熟風險
    # =====================================================

    if risk_index is not None:

        yellow_end = (
            high_index
            if high_index is not None
            else len(values) - 1
        )

        fig.add_trace(

            go.Scatter(

                x=times[
                    risk_index:
                    yellow_end + 1
                ],

                y=values[
                    risk_index:
                    yellow_end + 1
                ],

                mode="lines+markers",

                name="成熟風險上升",

                line=dict(
                    width=3,
                    color="#f59e0b"
                ),

                marker=dict(
                    size=5,
                    color="#f59e0b"
                ),

                hovertemplate=(
                    "%{x|%Y-%m-%d %H:%M}<br>"
                    "C₂H₄：%{y:.2f} ppm<br>"
                    "成熟階段：成熟風險上升"
                    "<extra></extra>"
                )
            )
        )

    # =====================================================
    # RED：高度成熟
    # =====================================================

    if high_index is not None:

        fig.add_trace(

            go.Scatter(

                x=times[
                    high_index:
                ],

                y=values[
                    high_index:
                ],

                mode="lines+markers",

                name="高度成熟",

                line=dict(
                    width=3,
                    color="#ef4444"
                ),

                marker=dict(
                    size=5,
                    color="#ef4444"
                ),

                hovertemplate=(
                    "%{x|%Y-%m-%d %H:%M}<br>"
                    "C₂H₄：%{y:.2f} ppm<br>"
                    "成熟階段：高度成熟"
                    "<extra></extra>"
                )
            )
        )

    # =====================================================
    # Neighbor Alert Event
    #
    # 紫色只代表「收到警示」
    # 不代表水果變成熟
    # =====================================================

    alert_index = tag[
        "alert_index"
    ]

    if alert_index is not None:

        alert_time = times[
            alert_index
        ]

        alert_value = values[
            alert_index
        ]

        # =================================================
        # 紫色垂直虛線
        # =================================================

        fig.add_vline(

            x=(
                alert_time.timestamp()
                * 1000
            ),

            line_width=2,

            line_dash="dash",

            line_color="#a855f7"
        )

        # =================================================
        # 紫色 ◆
        # =================================================

        fig.add_trace(

            go.Scatter(

                x=[
                    alert_time
                ],

                y=[
                    alert_value
                ],

                mode="markers",

                name="鄰近成熟警示",

                marker=dict(
                    size=14,
                    color="#a855f7",
                    symbol="diamond"
                ),

                hovertemplate=(
                    "<b>鄰近成熟警示接收起始</b><br>"
                    f"來源："
                    f"{tag['source']}<br>"
                    f"RSSI：約 "
                    f"{tag['rssi']} dBm<br>"
                    f"NREI："
                    f"{tag['nrei']}<br>"
                    "%{x|%Y-%m-%d %H:%M}"
                    "<extra></extra>"
                )
            )
        )

        # =================================================
        # 警示文字
        # 改放右下，避免被圖表頂端裁切
        # =================================================

        fig.add_annotation(

            x=alert_time,

            y=alert_value,

            text=(
                f"⚠ 收到 "
                f"{tag['source']} "
                f"成熟警示"
            ),

            showarrow=True,

            arrowhead=2,

            ax=75,

            ay=45,

            font=dict(
                size=12,
                color="#7e22ce"
            ),

            bgcolor="rgba(255,255,255,0.85)",

            bordercolor="#e9d5ff",

            borderwidth=1,

            borderpad=4
        )

    # =====================================================
    # Layout
    # =====================================================

    fig.update_layout(

        title=(
            f"{tag['id']}｜"
            "48 小時乙烯濃度與成熟階段變化"
        ),

        xaxis_title="時間",

        yaxis_title="C₂H₄ (ppm)",

        plot_bgcolor="white",

        paper_bgcolor="white",

        height=450,

        margin=dict(
            l=55,
            r=50,
            t=100,
            b=55
        ),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),

        hovermode="closest"
    )

    return fig


# =========================================================
# LAYOUT
# =========================================================

app.layout = html.Div(

    style=PAGE,

    children=[

        dcc.Store(
            id="batch-store"
        ),

        # =================================================
        # HEADER
        # =================================================

        html.H1(
            "🍌 水果冷鏈乙烯智慧監測系統"
        ),

        html.Div(

            (
                "Distributed Ethylene Sensing Network "
                "for Fruit Cold-Chain Monitoring"
            ),

            style={
                "color": "#64748b",
                "fontSize": "16px"
            }
        ),

        html.Br(),

        # =================================================
        # RFID GATE
        # =================================================

        html.Div(

            style=CARD,

            children=[

                html.H2(
                    "📡 UHF RFID Gate"
                ),

                html.P(
                    (
                        "模擬水果批次通過 RFID 閘門。"
                        "系統讀取各感測標籤的身分、"
                        "乙烯監測歷史與鄰近成熟警示紀錄。"
                    )
                ),

                html.Div(

                    id="gate-status",

                    children=(
                        "● 等待水果批次通過 RFID 閘門"
                    ),

                    style={
                        "padding": "12px",
                        "backgroundColor": "#f1f5f9",
                        "borderRadius": "8px",
                        "marginBottom": "15px"
                    }
                ),

                html.Button(

                    "模擬水果批次過閘",

                    id="scan-button",

                    n_clicks=0,

                    style={
                        "backgroundColor": "#2563eb",
                        "color": "white",
                        "border": "none",
                        "borderRadius": "8px",
                        "padding": "12px 24px",
                        "fontSize": "16px",
                        "cursor": "pointer"
                    }
                )
            ]
        ),

        html.Br(),

        # =================================================
        # DASHBOARD
        # =================================================

        html.Div(

            id="dashboard-content",

            style={
                "display": "none"
            },

            children=[

                # =========================================
                # BATCH
                # =========================================

                html.Div(
                    id="batch-info",
                    style=CARD
                ),

                html.Br(),

                # =========================================
                # SUMMARY
                # =========================================

                html.Div(

                    style={
                        "display": "grid",
                        "gridTemplateColumns":
                            "repeat(4, 1fr)",
                        "gap": "15px"
                    },

                    children=[

                        html.Div(
                            id="metric-tags",
                            style=METRIC
                        ),

                        html.Div(
                            id="metric-average",
                            style=METRIC
                        ),

                        html.Div(
                            id="metric-high",
                            style=METRIC
                        ),

                        html.Div(
                            id="metric-alert",
                            style=METRIC
                        )
                    ]
                ),

                html.Br(),

                # =========================================
                # MAIN CHARTS
                # =========================================

                html.Div(

                    style={
                        "display": "grid",
                        "gridTemplateColumns":
                            "1fr 1fr",
                        "gap": "20px"
                    },

                    children=[

                        # ---------------------------------
                        # C2H4
                        # ---------------------------------

                        html.Div(

                            style=CARD,

                            children=[

                                html.Div(

                                    [
                                        html.Span(
                                            "🔵 正常"
                                        ),

                                        html.Span(
                                            "　🟡 成熟風險上升"
                                        ),

                                        html.Span(
                                            "　🔴 高度成熟"
                                        ),
                                    ],

                                    style={
                                        "textAlign": "center",
                                        "fontSize": "13px",
                                        "color": "#64748b"
                                    }
                                ),

                                dcc.Graph(

                                    id="concentration-chart",

                                    config={
                                        "displayModeBar": False
                                    }
                                )
                            ]
                        ),

                        # ---------------------------------
                        # NETWORK
                        # ---------------------------------

                        html.Div(

                            style=CARD,

                            children=[

                                dcc.Graph(

                                    id="network-chart",

                                    config={
                                        "displayModeBar": False
                                    }
                                )
                            ]
                        )
                    ]
                ),

                html.Br(),

                # =========================================
                # INDIVIDUAL ANALYSIS
                # =========================================

                html.Div(

                    style=CARD,

                    children=[

                        html.H2(
                            "🔎 個別感測標籤分析"
                        ),

                        html.P(

                            (
                                "曲線顏色代表水果自身成熟階段："
                                "藍色為正常、黃色為成熟風險上升、"
                                "紅色為高度成熟；紫色 ◆ 為"
                                "鄰近成熟警示接收事件。"
                            ),

                            style={
                                "color": "#64748b"
                            }
                        ),

                        dcc.Dropdown(
                            id="tag-dropdown",
                            clearable=False
                        ),

                        html.Br(),

                        html.Div(
                            id="tag-metrics"
                        ),

                        html.Br(),

                        dcc.Graph(

                            id="history-chart",

                            config={
                                "displayModeBar": False
                            }
                        ),

                        html.Div(
                            id="analysis-card"
                        )
                    ]
                ),

                html.Br(),

                # =========================================
                # TAG CARDS
                # =========================================

                html.Div(

                    style=CARD,

                    children=[

                        html.H2(
                            "🏷 RFID Sensor Tags"
                        ),

                        html.Div(

                            id="tag-cards",

                            style={
                                "display": "grid",
                                "gridTemplateColumns":
                                    "repeat(auto-fit, minmax(190px, 1fr))",
                                "gap": "12px"
                            }
                        )
                    ]
                ),

                html.Br(),

                # =========================================
                # RESEARCH NOTE
                # =========================================

                html.Div(

                    [

                        html.Div(
                            (
                                "Prototype — Flexible Ethylene Sensor × "
                                "Battery-Assisted UHF RFID × "
                                "Neighbor Alert × Adaptive Sampling"
                            )
                        ),

                        html.Div(

                            (
                                "目前成熟判定門檻與 NREI "
                                "為研究原型設定；正式研究須透過"
                                "感測器校正、實際水果實驗與"
                                "統計分析建立判定條件。"
                            ),

                            style={
                                "marginTop": "5px"
                            }
                        ),

                        html.Div(

                            (
                                "Neighbor Alert 表示無線警示通訊紀錄，"
                                "不直接代表水果實際距離或乙烯影響的"
                                "因果關係。"
                            ),

                            style={
                                "marginTop": "3px"
                            }
                        )
                    ],

                    style={
                        "textAlign": "center",
                        "color": "#94a3b8",
                        "fontSize": "12px"
                    }
                )
            ]
        )
    ]
)


# =========================================================
# CALLBACK
# RFID GATE
# =========================================================

@app.callback(

    Output(
        "batch-store",
        "data"
    ),

    Output(
        "gate-status",
        "children"
    ),

    Input(
        "scan-button",
        "n_clicks"
    ),

    prevent_initial_call=True
)

def scan_batch(n_clicks):

    batch = generate_batch()

    status = (
        f"● RFID 讀取完成｜"
        f"批次 {batch['batch_id']}｜"
        f"共偵測 {len(batch['tags'])} 個感測標籤"
    )

    return (
        batch,
        status
    )


# =========================================================
# CALLBACK
# MAIN DASHBOARD
# =========================================================

@app.callback(

    Output(
        "dashboard-content",
        "style"
    ),

    Output(
        "batch-info",
        "children"
    ),

    Output(
        "metric-tags",
        "children"
    ),

    Output(
        "metric-average",
        "children"
    ),

    Output(
        "metric-high",
        "children"
    ),

    Output(
        "metric-alert",
        "children"
    ),

    Output(
        "concentration-chart",
        "figure"
    ),

    Output(
        "network-chart",
        "figure"
    ),

    Output(
        "tag-dropdown",
        "options"
    ),

    Output(
        "tag-dropdown",
        "value"
    ),

    Output(
        "tag-cards",
        "children"
    ),

    Input(
        "batch-store",
        "data"
    )
)

def update_dashboard(batch):

    if not batch:

        return (
            {"display": "none"},
            "",
            "",
            "",
            "",
            "",
            go.Figure(),
            go.Figure(),
            [],
            None,
            []
        )

    tags = batch["tags"]

    # =====================================================
    # Statistics
    # =====================================================

    average = (
        sum(
            tag["ethylene"]
            for tag in tags
        )
        / len(tags)
    )

    high_count = sum(
        tag["stage"] == "高度成熟"
        for tag in tags
    )

    alert_count = sum(
        tag["source"] is not None
        for tag in tags
    )

    # =====================================================
    # Batch Info
    # =====================================================

    batch_info = html.Div([

        html.H2(
            "📦 冷鏈批次資訊"
        ),

        html.Div(
            f"Batch ID：{batch['batch_id']}"
        ),

        html.Div(
            f"RFID Gate 讀取時間：{batch['time']}"
        ),

        html.Div(

            (
                "資料內容：Tag ID、C₂H₄、48h EEI、"
                "dC/dt、成熟階段與 Neighbor Alert 紀錄"
            ),

            style={
                "color": "#64748b",
                "marginTop": "6px"
            }
        )
    ])

    # =====================================================
    # Metrics
    # =====================================================

    metric_tags = [

        html.Div(
            "偵測標籤"
        ),

        html.H2(
            str(
                len(tags)
            )
        )
    ]

    metric_average = [

        html.Div(
            "平均 C₂H₄"
        ),

        html.H2(
            f"{average:.2f} ppm"
        )
    ]

    metric_high = [

        html.Div(
            "高度成熟"
        ),

        html.H2(

            str(
                high_count
            ),

            style={
                "color": "#ef4444"
            }
        )
    ]

    metric_alert = [

        html.Div(
            "曾接收鄰近警示"
        ),

        html.H2(

            str(
                alert_count
            ),

            style={
                "color": "#a855f7"
            }
        )
    ]

    # =====================================================
    # CURRENT C2H4 BAR CHART
    # =====================================================

    colors = []

    for tag in tags:

        if tag["stage"] == "高度成熟":

            colors.append(
                "#ef4444"
            )

        elif (
            tag["stage"]
            == "成熟風險上升"
        ):

            colors.append(
                "#f59e0b"
            )

        else:

            colors.append(
                "#3b82f6"
            )

    concentration_fig = go.Figure()

    concentration_fig.add_trace(

        go.Bar(

            x=[
                tag["id"]
                for tag in tags
            ],

            y=[
                tag["ethylene"]
                for tag in tags
            ],

            marker_color=colors,

            text=[
                f"{tag['ethylene']} ppm"
                for tag in tags
            ],

            textposition="outside",

            cliponaxis=False,

            hovertemplate=(
                "<b>%{x}</b><br>"
                "C₂H₄：%{y:.2f} ppm"
                "<extra></extra>"
            ),

            showlegend=False
        )
    )

    # =====================================================
    # 門檻線
    #
    # 不在圖內加文字
    # 避免壓到柱狀圖
    # =====================================================

    concentration_fig.add_hline(

        y=RISK_THRESHOLD,

        line_dash="dash",

        line_color="#f59e0b",

        line_width=2
    )

    concentration_fig.add_hline(

        y=HIGH_RIPENESS_THRESHOLD,

        line_dash="dash",

        line_color="#ef4444",

        line_width=2
    )

    concentration_fig.update_layout(

        title={
            "text":
                "Current Ethylene Concentration｜"
                "目前乙烯濃度",
            "x": 0.03
        },

        xaxis_title=(
            "RFID Sensor Tag"
        ),

        yaxis_title=(
            "C₂H₄ (ppm)"
        ),

        plot_bgcolor="white",

        paper_bgcolor="white",

        showlegend=False,

        height=430,

        margin=dict(
            l=55,
            r=25,
            t=70,
            b=55
        )
    )

    # =====================================================
    # Network
    # =====================================================

    network_fig = create_network(
        batch
    )

    # =====================================================
    # Dropdown
    # =====================================================

    options = []

    for tag in tags:

        if tag["stage"] == "高度成熟":

            icon = "🔴"

        elif (
            tag["stage"]
            == "成熟風險上升"
        ):

            icon = "🟡"

        else:

            icon = "🔵"

        alert_icon = (
            "　⚠ 鄰近警示紀錄"
            if tag["source"] is not None
            else ""
        )

        options.append({

            "label": (
                f"{icon} {tag['id']}｜"
                f"{tag['stage']}"
                f"{alert_icon}"
            ),

            "value":
                tag["id"]
        })

    # 優先選擇有鄰近警示紀錄的 Tag
    alerted = [
        tag
        for tag in tags
        if tag["source"] is not None
    ]

    if alerted:

        default_value = (
            alerted[0]["id"]
        )

    else:

        default_value = (
            tags[0]["id"]
        )

    # =====================================================
    # TAG CARDS
    # =====================================================

    cards = []

    for tag in tags:

        if tag["stage"] == "高度成熟":

            color = "#ef4444"

            background = "#fef2f2"

            icon = "🔴"

        elif (
            tag["stage"]
            == "成熟風險上升"
        ):

            color = "#f59e0b"

            background = "#fffbeb"

            icon = "🟡"

        else:

            color = "#3b82f6"

            background = "#eff6ff"

            icon = "🔵"

        children = [

            html.H3(

                f"{icon} {tag['id']}",

                style={
                    "margin":
                        "0 0 8px 0"
                }
            ),

            html.Div(

                tag["stage"],

                style={
                    "fontWeight": "bold",
                    "color": color
                }
            ),

            html.Div(
                f"C₂H₄："
                f"{tag['ethylene']} ppm"
            ),

            html.Div(
                f"48h EEI："
                f"{tag['eei']} ppm·h"
            ),

            html.Div(
                f"dC/dt："
                f"{tag['rate']:+.2f} ppm/h"
            )
        ]

        # =================================================
        # Neighbor Alert 額外資訊
        # =================================================

        if tag["source"] is not None:

            children.append(

                html.Div(

                    (
                        f"⚠ 警示來源："
                        f"{tag['source']}｜"
                        f"RSSI "
                        f"{tag['rssi']} dBm"
                    ),

                    style={
                        "fontSize": "12px",
                        "color": "#7e22ce",
                        "marginTop": "8px"
                    }
                )
            )

        cards.append(

            html.Div(

                style={
                    "padding": "15px",
                    "borderRadius": "12px",
                    "backgroundColor":
                        background,
                    "border":
                        f"1px solid {color}"
                },

                children=children
            )
        )

    return (

        {"display": "block"},

        batch_info,

        metric_tags,

        metric_average,

        metric_high,

        metric_alert,

        concentration_fig,

        network_fig,

        options,

        default_value,

        cards
    )


# =========================================================
# CALLBACK
# INDIVIDUAL TAG ANALYSIS
# =========================================================

@app.callback(

    Output(
        "tag-metrics",
        "children"
    ),

    Output(
        "history-chart",
        "figure"
    ),

    Output(
        "analysis-card",
        "children"
    ),

    Input(
        "tag-dropdown",
        "value"
    ),

    State(
        "batch-store",
        "data"
    )
)

def update_tag_analysis(
    selected_tag,
    batch
):

    if (
        not batch
        or not selected_tag
    ):

        return (
            "",
            go.Figure(),
            ""
        )

    tag = next(

        (
            item
            for item in batch["tags"]
            if item["id"] == selected_tag
        ),

        None
    )

    if tag is None:

        return (
            "",
            go.Figure(),
            ""
        )

    # =====================================================
    # METRICS
    # =====================================================

    tag_metrics = html.Div(

        style={
            "display": "grid",
            "gridTemplateColumns":
                "repeat(2, 1fr)",
            "gap": "12px"
        },

        children=[

            html.Div(

                style=METRIC,

                children=[

                    html.Div(
                        "目前 C₂H₄"
                    ),

                    html.H3(
                        f"{tag['ethylene']} ppm"
                    )
                ]
            ),

            html.Div(

                style=METRIC,

                children=[

                    html.Div(
                        "48h EEI"
                    ),

                    html.H3(
                        f"{tag['eei']} ppm·h"
                    )
                ]
            ),

            html.Div(

                style=METRIC,

                children=[

                    html.Div(
                        "dC/dt"
                    ),

                    html.H3(
                        f"{tag['rate']:+.2f} ppm/h"
                    )
                ]
            ),

            html.Div(

                style=METRIC,

                children=[

                    html.Div(
                        "NREI（Prototype）"
                    ),

                    html.H3(
                        str(
                            tag["nrei"]
                        )
                    )
                ]
            )
        ]
    )

    # =====================================================
    # HISTORY
    # =====================================================

    history_fig = (
        create_history_figure(
            tag
        )
    )

    # =====================================================
    # 自身成熟狀態
    # =====================================================

    if tag["stage"] == "高度成熟":

        title = (
            "🔴 高度成熟"
        )

        description = (
            "本標籤自身的乙烯濃度已進入"
            "目前研究原型設定之高度成熟區間。"
        )

        background = (
            "#fef2f2"
        )

        border_color = (
            "#ef4444"
        )

    elif (
        tag["stage"]
        == "成熟風險上升"
    ):

        title = (
            "🟡 成熟風險上升"
        )

        description = (
            "本標籤自身乙烯濃度已進入"
            "成熟風險上升區間，建議持續"
            "追蹤其成熟變化。"
        )

        background = (
            "#fffbeb"
        )

        border_color = (
            "#f59e0b"
        )

    else:

        title = (
            "🔵 正常監測"
        )

        description = (
            "目前本標籤自身乙烯濃度"
            "尚未進入研究原型設定之"
            "成熟風險區間。"
        )

        background = (
            "#eff6ff"
        )

        border_color = (
            "#3b82f6"
        )

    analysis_children = [

        html.H3(
            title,
            style={
                "marginTop": "0"
            }
        ),

        html.P(
            description
        ),

        html.P(

            (
                f"目前 C₂H₄："
                f"{tag['ethylene']} ppm｜"
                f"48h EEI："
                f"{tag['eei']} ppm·h｜"
                f"dC/dt："
                f"{tag['rate']:+.2f} ppm/h"
            )
        )
    ]

    # =====================================================
    # NEIGHBOR ALERT
    # =====================================================

    if tag["source"] is not None:

        alert_time = (
            datetime.fromisoformat(
                tag["alert_time"]
            )
        )

        analysis_children += [

            html.Hr(),

            html.H4(

                "⚠ 鄰近成熟警示紀錄",

                style={
                    "color": "#7e22ce"
                }
            ),

            html.P(

                (
                    f"{selected_tag} 曾於 "
                    f"{alert_time.strftime('%Y-%m-%d %H:%M')} "
                    f"接收到高度成熟節點 "
                    f"{tag['source']} "
                    "發出的成熟警示。"
                )
            ),

            html.P(

                (
                    f"RSSI：約 "
                    f"{tag['rssi']} dBm｜"
                    f"警示紀錄時間："
                    f"{tag['exposure_hours']} h｜"
                    f"NREI："
                    f"{tag['nrei']}"
                )
            ),

            html.P(

                (
                    "收到鄰近成熟警示後，"
                    "系統可啟動 Adaptive Sampling，"
                    "例如由每 30 分鐘採樣一次"
                    "暫時提高為每 5 分鐘一次，"
                    "以追蹤後續 C₂H₄ 變化。"
                )
            ),

            html.P(

                (
                    "注意：Neighbor Alert 僅表示"
                    "此標籤曾接收到鄰近高度成熟節點"
                    "的無線警示。RSSI 僅作為"
                    "相對鄰近程度參考，不能單獨"
                    "判定實際距離，也不能據此證明"
                    "乙烯影響的直接因果關係。"
                ),

                style={
                    "fontSize": "13px",
                    "color": "#64748b"
                }
            )
        ]

    else:

        analysis_children += [

            html.Hr(),

            html.P(

                (
                    "目前沒有鄰近成熟警示接收紀錄。"
                ),

                style={
                    "color": "#64748b"
                }
            )
        ]

    analysis = html.Div(

        style={
            "backgroundColor":
                background,
            "borderLeft":
                f"5px solid {border_color}",
            "padding":
                "16px",
            "borderRadius":
                "8px"
        },

        children=analysis_children
    )

    return (
        tag_metrics,
        history_fig,
        analysis
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )