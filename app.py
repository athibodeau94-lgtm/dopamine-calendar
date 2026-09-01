import datetime
import json
import os
import chinese_calendar as cn_cal
import holidays
import streamlit as st
from streamlit_calendar import calendar

st.set_page_config(
    page_title="Day Day Up", layout="wide", initial_sidebar_state="collapsed"
)

# 注入 CSS：页面紧凑布局 + 图例靠左 + 莫兰迪视觉
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    h1 {
        color: #37474F !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
    }
    .fc {
        max-height: 70vh !important;
        font-size: 13px !important;
    }
    .fc-scroller {
        overflow: hidden !important;
    }
    div[data-testid="stDialog"] > div {
        border-radius: 12px !important;
        border: 1px solid #CFD8DC;
    }
    .metric-card {
        background-color: #ECEFF1;
        border-radius: 8px;
        padding: 10px 15px;
        text-align: center;
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


# 2. 读取节假日（防超年报错安全校验）
@st.cache_data
def get_holidays():
  current_year = datetime.datetime.now().year
  years = [current_year - 1, current_year, current_year + 1]

  holiday_events = []

  # 中国法定节假日 (chinesecalendar)
  start_date = datetime.date(current_year - 1, 1, 1)
  end_date = datetime.date(current_year + 1, 12, 31)

  for single_date in (
      start_date + datetime.timedelta(days=n)
      for n in range((end_date - start_date).days + 1)
  ):
    try:
      on_holiday, holiday_name = cn_cal.get_holiday_detail(single_date)
      date_str = single_date.strftime("%Y-%m-%d")

      if on_holiday and holiday_name:
        holiday_events.append({
            "id": f"cn_holiday_{date_str}",
            "title": f"🇨🇳 {holiday_name} (法定休息)",
            "start": date_str,
            "color": "#D98880",  # 浅陶红
            "allDay": True,
            "editable": False,
            "is_holiday": True,
        })
      elif not on_holiday and cn_cal.is_workday(single_date):
        if single_date.weekday() >= 5:  # 周末调休补班
          holiday_events.append({
              "id": f"cn_workday_{date_str}",
              "title": "🇨🇳 调休上班",
              "start": date_str,
              "color": "#90AACB",  # 浅柔蓝
              "allDay": True,
              "editable": False,
              "is_holiday": True,
          })
    except NotImplementedError:
      # 超出库数据范围的未来年份跳过，防止报错
      continue

  # 美国节假日
  us_holidays = holidays.US(years=years)
  for date, name in us_holidays.items():
    holiday_events.append({
        "id": f"us_holiday_{date}",
        "title": f"🇺🇸 {name}",
        "start": date.strftime("%Y-%m-%d"),
        "color": "#B0BEC5",  # 浅雾灰
        "allDay": True,
        "editable": False,
        "is_holiday": True,
    })

  return holiday_events


# 3. 弹窗设置排班/事项
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

  # 浅色莫兰迪调色盘
  color_map = {
      "工作日": "#90AACB",  # 浅柔蓝
      "休息日": "#B5C99A",  # 浅草绿
      "值班日": "#E6C280",  # 浅暖杏
      "加班日": "#E08E79",  # 浅陶红
  }

  if category == "排班标记":
    shift = st.selectbox(
        "班别",
        ["工作日", "休息日", "值班日", "加班日"],
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
    selected_color = "#B39DDB"  # 浅丁香紫

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


# 4. 主界面展示与标题
st.title("Day Day Up")

# 5. 总视图与月度排班天数统计面板
with st.expander("📊 查看排班统计总视图（上月/上年/自定义数据）", expanded=False):
  col_s1, col_s2 = st.columns([1, 2])
  with col_s1:
    view_type = st.radio("统计范围", ["按月份", "按年份"], horizontal=True)
  with col_s2:
    today = datetime.date.today()
    if view_type == "按月份":
      target_year = st.number_input("年份", value=today.year, step=1)
      target_month = st.selectbox(
          "月份", list(range(1, 13)), index=today.month - 1
      )
      filter_prefix = f"{target_year}-{target_month:02d}"
    else:
      target_year = st.number_input("年份", value=today.year, step=1)
      filter_prefix = f"{target_year}"

  # 统计逻辑
  counts = {"工作日": 0, "休息日": 0, "值班日": 0, "加班日": 0, "事项": 0}
  for ev in st.session_state.events:
    if ev.get("start", "").startswith(filter_prefix):
      title = ev.get("title", "")
      if "[工作日]" in title:
        counts["工作日"] += 1
      elif "[休息日]" in title:
        counts["休息日"] += 1
      elif "[值班日]" in title:
        counts["值班日"] += 1
      elif "[加班日]" in title:
        counts["加班日"] += 1
      elif "📝" in title:
        counts["事项"] += 1

  c1, c2, c3, c4, c5 = st.columns(5)
  c1.metric("🔵 工作日", f"{counts['工作日']} 天")
  c2.metric("🟢 休息日", f"{counts['休息日']} 天")
  c3.metric("🟡 值班日", f"{counts['值班日']} 天")
  c4.metric("🔴 加班日", f"{counts['加班日']} 天")
  c5.metric("🟣 待办事项", f"{counts['事项']} 个")


# 6. 图例说明（靠左排列，隐藏代码）
legend_cols = st.columns([1, 1, 1, 1, 1, 1, 6])
legend_cols[0].markdown("🔵 **工作日**")
legend_cols[1].markdown("🟢 **休息日**")
legend_cols[2].markdown("🟡 **值班日**")
legend_cols[3].markdown("🔴 **加班日**")
legend_cols[4].markdown("🟣 **事项**")
legend_cols[5].markdown("⚪ **美节**")

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

# 7. 监听日历交互（安全兼容校验）
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
