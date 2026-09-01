
import datetime
import json
import os
import holidays
import streamlit as st
from streamlit_calendar import calendar

st.set_page_config(
    page_title="多巴胺排班日历", layout="wide", initial_sidebar_state="collapsed"
)

# 注入 CSS 提升多巴胺视觉质感
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FAFAFA;
    }
    h1 {
        background: linear-gradient(45deg, #FF1744, #FF9100, #00E676, #2979FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    div[data-testid="stDialog"] > div {
        border-radius: 20px !important;
        border: 2px solid #FF4081;
    }
    </style>
""",
    unsafe_allow_html=True,
)

DATA_FILE = "events.json"


# 1. 数据持久化读取与保存
def load_events():
  if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  return []


def save_events(events):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(events, f, ensure_ascii=False, indent=2)


if "events" not in st.session_state:
  st.session_state.events = load_events()


# 2. 读取今明两年的中美法定节假日（多巴胺配色）
@st.cache_data
def get_holidays():
  current_year = datetime.datetime.now().year
  years = [current_year, current_year + 1]

  cn_holidays = holidays.China(years=years)
  us_holidays = holidays.US(years=years)

  holiday_events = []
  # 中国节假日：热带火山红 (#FF1744)
  for date, name in cn_holidays.items():
    holiday_events.append({
        "id": f"holiday_cn_{date}",
        "title": f"🇨🇳 {name}",
        "start": date.strftime("%Y-%m-%d"),
        "color": "#FF1744",
        "allDay": True,
        "editable": False,
        "is_holiday": True,
    })
  # 美国节假日：电光蓝色 (#2979FF)
  for date, name in us_holidays.items():
    holiday_events.append({
        "id": f"holiday_us_{date}",
        "title": f"🇺🇸 {name}",
        "start": date.strftime("%Y-%m-%d"),
        "color": "#2979FF",
        "allDay": True,
        "editable": False,
        "is_holiday": True,
    })
  return holiday_events


# 3. 交互弹窗：点击日期添加/修改排班与事项
@st.dialog("🌈 记录你的多巴胺日程")
def manage_event_dialog(selected_date):
  st.write(f"选中日期：**{selected_date}**")

  existing_event_index = None
  existing_event = None
  for idx, ev in enumerate(st.session_state.events):
    if ev.get("start") == selected_date:
      existing_event_index = idx
      existing_event = ev
      break

  category = st.radio("类型", ["排班标记", "自定义事项"], horizontal=True)

  # 多巴胺高活力调色盘
  color_map = {
      "普通工作日": "#00E676",  # 活力薄荷绿
      "休息日": "#FFD600",  # 明亮阳光黄
      "值班日": "#FF9100",  # 热情蜜桃橙
      "加班日": "#FF1744",  # 火山热带红
  }

  if category == "排班标记":
    shift = st.selectbox(
        "班别",
        ["普通工作日", "休息日", "值班日", "加班日"],
        index=0,
    )
    title_text = f"[{shift}]"
    selected_color = color_map[shift]
  else:
    todo_text = st.text_input(
        "事项描述",
        value=existing_event["title"].replace("📝 ", "")
        if existing_event and "📝 " in existing_event["title"]
        else "",
    )
    title_text = f"📝 {todo_text}"
    selected_color = "#D500F9"  # 霓虹电光紫

  col1, col2 = st.columns(2)

  with col1:
    if st.button("保存", type="primary", use_container_width=True):
      if category == "自定义事项" and not todo_text.strip():
        st.error("请填写事项！")
        return

      new_data = {
          "id": f"custom_{selected_date}",
          "title": title_text,
          "start": selected_date,
          "color": selected_color,
          "allDay": True,
          "is_holiday": False,
      }

      if existing_event_index is not None:
        st.session_state.events[existing_event_index] = new_data
      else:
        st.session_state.events.append(new_data)

      save_events(st.session_state.events)
      st.rerun()

  with col2:
    if existing_event_index is not None:
      if st.button("删除记录", type="secondary", use_container_width=True):
        st.session_state.events.pop(existing_event_index)
        save_events(st.session_state.events)
        st.rerun()


# 4. 主界面：排班与日历展现
st.title("📅 多巴胺智能排班日历")
st.caption("✨ 点击任意日期直接设置排班或事项，碰撞你的彩色工作日程！")

# 图例说明
cols = st.columns(6)
cols[0].markdown("🟢 **工作日** `#00E676`", unsafe_allow_html=True)
cols[1].markdown("🟡 **休息日** `#FFD600`", unsafe_allow_html=True)
cols[2].markdown("🟠 **值班日** `#FF9100`", unsafe_allow_html=True)
cols[3].markdown("🔴 **加班日** `#FF1744`", unsafe_allow_html=True)
cols[4].markdown("🟣 **事项** `#D500F9`", unsafe_allow_html=True)
cols[5].markdown("🔵 **美节** `#2979FF`", unsafe_allow_html=True)

all_events = get_holidays() + st.session_state.events

calendar_options = {
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek",
    },
    "initialView": "dayGridMonth",
    "selectable": True,
    "editable": False,
}

cal_output = calendar(events=all_events, options=calendar_options)

# 5. 监听点击交互事件
if cal_output.get("dateClick"):
  clicked_date = cal_output["dateClick"]["dateStr"]
  manage_event_dialog(clicked_date)

elif cal_output.get("eventClick"):
  clicked_event = cal_output["eventClick"]["event"]
  if not clicked_event.get("extendedProps", {}).get("is_holiday", False):
    event_date = clicked_event["start"].split("T")[0]
    manage_event_dialog(event_date)
