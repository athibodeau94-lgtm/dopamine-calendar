import datetime
import json
import os
import holidays
import streamlit as st
from streamlit_calendar import calendar

st.set_page_config(
    page_title="Day Day Up", layout="wide", initial_sidebar_state="collapsed"
)

# 注入 CSS：压缩顶部边距与日历高度，保证一屏完整显示 1-31 号
st.markdown(
    """
    <style>
    /* 压缩 Streamlit 默认外边距 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    h1 {
        color: #4A5568 !important;
        font-weight: 700 !important;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    /* 强制调整日历整体高度与字体 */
    .fc {
        max-height: 72vh !important;
        font-size: 13px !important;
    }
    .fc-scroller {
        overflow: hidden !important;
    }
    div[data-testid="stDialog"] > div {
        border-radius: 12px !important;
        border: 1px solid #B8C0CC;
    }
    </style>
""",
    unsafe_allow_html=True,
)

DATA_FILE = "events.json"


# 1. 数据持久化
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


# 2. 读取中美节假日（莫兰迪配色）
@st.cache_data
def get_holidays():
  current_year = datetime.datetime.now().year
  years = [current_year, current_year + 1]

  cn_holidays = holidays.China(years=years)
  us_holidays = holidays.US(years=years)

  holiday_events = []
  # 中国节假日：莫兰迪豆沙红 (#C97A7E)
  for date, name in cn_holidays.items():
    holiday_events.append({
        "id": f"holiday_cn_{date}",
        "title": f"🇨🇳 {name}",
        "start": date.strftime("%Y-%m-%d"),
        "color": "#C97A7E",
        "allDay": True,
        "editable": False,
        "is_holiday": True,
    })
  # 美国节假日：莫兰迪雾霾蓝 (#6C8EBF)
  for date, name in us_holidays.items():
    holiday_events.append({
        "id": f"holiday_us_{date}",
        "title": f"🇺🇸 {name}",
        "start": date.strftime("%Y-%m-%d"),
        "color": "#6C8EBF",
        "allDay": True,
        "editable": False,
        "is_holiday": True,
    })
  return holiday_events


# 3. 点击日期弹窗设置排班/事项
@st.dialog("📅 设定日程与排班")
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

  # 莫兰迪调色盘
  color_map = {
      "普通工作日": "#84A98C",  # 鼠尾草绿
      "休息日": "#B0C4DE",  # 冰川蓝/灰
      "值班日": "#E5B869",  # 燕麦黄
      "加班日": "#D98880",  # 暖陶红
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
    selected_color = "#A29BFE"  # 薰衣草紫

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


# 4. 主界面展示
st.title("☀️ Day Day Up")

# 图例说明
cols = st.columns(6)
cols[0].markdown("🟢 **工作日** `#84A98C`", unsafe_allow_html=True)
cols[1].markdown("⚪ **休息日** `#B0C4DE`", unsafe_allow_html=True)
cols[2].markdown("🟡 **值班日** `#E5B869`", unsafe_allow_html=True)
cols[3].markdown("🔴 **加班日** `#D98880`", unsafe_allow_html=True)
cols[4].markdown("🟣 **事项** `#A29BFE`", unsafe_allow_html=True)
cols[5].markdown("🔵 **美节** `#6C8EBF`", unsafe_allow_html=True)

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
    "height": "auto",
}

cal_output = calendar(events=all_events, options=calendar_options)

# 5. 监听日历交互（安全兼容校验）
if cal_output and isinstance(cal_output, dict):
  if "dateClick" in cal_output:
    date_click_data = cal_output["dateClick"]
    clicked_date = date_click_data.get("dateStr") or date_click_data.get("date")
    if clicked_date:
      clicked_date = str(clicked_date).split("T")[0]
      manage_event_dialog(clicked_date)

  elif "eventClick" in cal_output:
    event_data = cal_output["eventClick"].get("event", {})
    if not event_data.get("extendedProps", {}).get("is_holiday", False):
      start_time = event_data.get("start")
      if start_time:
        event_date = str(start_time).split("T")[0]
        manage_event_dialog(event_date)
