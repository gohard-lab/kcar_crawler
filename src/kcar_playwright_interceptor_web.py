import streamlit as st
import pandas as pd
import time
import sys
import asyncio
import io
import os

from tracker_web import log_app_usage


@st.dialog("⭐ Support Polymath Developer Automation Tool")
def show_star_popup_web():
    # 팝업 노출 트래커 기록
    log_app_usage("Kcar_crawler", "star_prompt_displayed", details={"ui": "streamlit_dialog"})
    
    st.warning(
        "💡 유용하게 사용하셨나요? 소스코드만 날름 가져가는 분들이 많습니다. "
        "개발자의 땀과 노력에 대한 최소한의 예의로 깃허브 Star⭐를 부탁드립니다!\n\n"
        "Did you find this useful? Please show some basic courtesy for the developer's hard work by leaving a GitHub Star⭐."
    )
    
    # 깃허브 Star 유도 버튼
    st.link_button("👉 깃허브로 이동하여 Star 누르기", "https://github.com/gohard-lab/kcar_crawler")


# ✅ 변경 후 (최초 1회 접속 시에만 실행됨)
if "has_logged_execution" not in st.session_state:
    show_star_popup_web()

    # 함수가 성공했는지(True) 로딩 때문에 실패했는지(False) 결과를 받습니다.
    is_logged = log_app_usage("Kcar_crawler", "crawler_opened")
    
    # 완전히 DB 기록에 성공했을 때만 도장을 쾅 찍어줍니다!
    if is_logged:
        st.session_state["has_logged_execution"] = True


# 스트림릿 클라우드 깡통 서버에 크롬 브라우저를 강제로 설치하게 만드는 마법의 주문
os.system("playwright install chromium")

# --- [윈도우 환경 Streamlit + Playwright 충돌 방지 코드] ---
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# -----------------------------------------------------------

from playwright.sync_api import sync_playwright

# --- 1. Playwright API 인터셉트 엔진 (정문 돌파 완성형) ---
def intercept_kcar_api(keyword):
    """메인 페이지로 진입하여 고유한 Placeholder를 찾아 검색하는 안정적인 방식"""
    time.sleep(1) 
    
    with sync_playwright() as p:
        # 💡 [수정 포인트 1] headless=False 로 변경하여 브라우저 화면을 띄웁니다.
        # 💡 [수정 포인트 2] slow_mo=500 을 추가해서 봇의 행동을 0.5초씩 느리게 만듭니다.
        browser = p.chromium.launch(headless=True, slow_mo=500)
        # browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        target_api_pattern = "**/search/list**"

        try:
            print(f"[{keyword}] 정문(메인 페이지)으로 진입합니다...")
            page.goto("https://www.kcar.com", timeout=30000)
            
            search_input = page.get_by_placeholder("차량을 검색하세요.")
            search_input.wait_for(state="visible", timeout=10000)
            
            search_input.fill(keyword)
            print("검색어 입력 완료. 엔터키를 누르고 암호화 통신을 기다립니다...")
            
            with page.expect_response(target_api_pattern, timeout=15000) as response_info:
                search_input.press("Enter")
            
            response = response_info.value
            
            if response.ok:
                data = response.json()
                rows = data.get('data', {}).get('rows', [])
                
                parsed_data = []
                for car in rows:
                    brand = car.get('mnuftrNm', '브랜드불명')
                    model = car.get('grdNm') or car.get('carNm', '모델명불명') 
                    
                    raw_year = car.get('mfgDt') or car.get('mnfctYy', '연식불명')
                    
                    if isinstance(raw_year, str) and raw_year.isdigit():
                        if len(raw_year) >= 6:
                            display_year = f"{raw_year[:4]}년 {raw_year[4:6]}월"
                        elif len(raw_year) == 4:
                            display_year = f"{raw_year}년"
                        else:
                            display_year = raw_year
                    else:
                        display_year = str(raw_year)
                    
                    price_str = car.get('rentPriceAvc') or car.get('prc', '0')
                    price_int = int(str(price_str).replace(',', '')) if str(price_str).isdigit() else 0
                    
                    if price_int > 0:
                        parsed_data.append({
                            "브랜드": brand, 
                            "모델명": model,
                            "연식": display_year,
                            "매물 가격 (만 원)": price_int
                        })
                        
                return parsed_data
            else:
                return None
                
        except Exception as e:
            print(f"\n[크롤링 상세 에러 분석]: {e}")
            return None
        finally:
            time.sleep(2) 
            browser.close()

# --- 2. Streamlit 웹 대시보드 UI ---
st.set_page_config(page_title="내 차 가치 분석기", page_icon="🚗", layout="wide")

st.title("🚗 K Car 중고차 감가 방어율 분석기 (Playwright 엔진)")
st.markdown("현업의 API 통신 가로채기 방식으로 실제 100% 직영 매물 데이터를 동적 수집하여 분석합니다.")

# 💡 [핵심 추가] 크롤링한 데이터와 당시의 검색 조건을 담아둘 세션 메모리 초기화
if "is_analyzed" not in st.session_state:
    st.session_state.is_analyzed = False
if "car_data" not in st.session_state:
    st.session_state.car_data = None
if "saved_target_car" not in st.session_state:
    st.session_state.saved_target_car = ""
if "saved_new_car_price" not in st.session_state:
    st.session_state.saved_new_car_price = 0
# 💡 [신규 추가] DB에 저장해야 할 기록을 올려둘 '로깅 대기열'
if "pending_log" not in st.session_state:
    st.session_state.pending_log = None

with st.sidebar:
    st.header("설정 (Settings)")
    target_car = st.text_input("분석할 차종을 입력하세요", placeholder="예: 그랜저, 아반떼", value="그랜저")
    
    new_car_price = st.number_input(
        "해당 차종의 신차 출고가 (만 원)", 
        min_value=1000, max_value=20000, value=3500, step=100
    )
    
    analyze_btn = st.button("데이터 탈취 및 분석 시작", type="primary", use_container_width=True)

# --- [신규 추가] 처리 완료된 주문 번호를 모아두는 장부 ---
if "completed_logs" not in st.session_state:
    st.session_state.completed_logs = set()
if "current_log_task" not in st.session_state:
    st.session_state.current_log_task = None

# --- 3. 버튼 클릭: 데이터 수집 및 메모리 백업 ---
if analyze_btn:
    if not target_car:
        st.warning("차종을 먼저 입력해 주세요!")
    else:
        with st.spinner(f"투명 브라우저가 '{target_car}' 데이터를 암호화망을 뚫고 가로채는 중입니다..."):
            car_data_list = intercept_kcar_api(target_car)
        
        if not car_data_list:
            st.error("데이터를 수집하지 못했습니다. 검색어가 정확한지 확인해 주세요.")

            # 💡 [핵심 수정 1] 실패했을 때는 기존 메모리를 깨끗하게 비워버립니다!
            st.session_state.car_data = None
            st.session_state.is_analyzed = False
        else:
            # 💡 데이터를 화면에 바로 그리지 않고 메모리에 안전하게 백업합니다.
            st.session_state.car_data = car_data_list
            st.session_state.saved_target_car = target_car
            st.session_state.saved_new_car_price = new_car_price
            st.session_state.is_analyzed = True
            
            # 💡 [신규] 버튼을 누른 바로 그 시간(초)을 합쳐서 절대 중복되지 않는 주문 번호 발급!
            task_id = f"{target_car}_{int(time.time())}"
            st.session_state.current_log_task = {
                "id": task_id,
                "car": target_car,
                "price": new_car_price
            }

            # # 여기서 Supabase 로깅을 실행합니다. (새로고침이 발생해도 이제 안전합니다)
            # try:
            #     tracking_details = {
            #         "car": target_car,
            #         "price": new_car_price
            #     }
            #     log_app_usage("Kcar_crawler", "click_analyze", tracking_details)
            # except Exception as e:
            #     # 에러 로그는 개발자 확인용으로 터미널에 조용히 남깁니다.
            #     print(f"[Supabase 로깅 에러 발생]: {e}")


# --- 💡 [신규 로직] 백그라운드 로깅 처리기 ---
# 대기열에 처리해야 할 로깅 임무가 남아있다면, 화면 새로고침과 무관하게 알아서 시도합니다.
if st.session_state.pending_log is not None:
    # 1. 대기열에서 데이터를 미리 빼냅니다. (이후 새로고침 당해도 대기열은 이미 비어있음!)
    current_log_data = st.session_state.pending_log
    st.session_state.pending_log = None

    try:
        # DB 저장을 시도합니다. ("LOADING" 상태면 False를 반환할 것입니다)
        is_logged = log_app_usage(
            "Kcar_crawler", 
            "click_analyze", 
            current_log_data
        )
        
        # 완전히 DB 기록에 성공(True)했을 때만 대기열을 비워줍니다.
        # 만약 "LOADING" 때문에 실패했다면, 다음 새로고침 때 다시 시도합니다!
        if is_logged:
            st.session_state.pending_log = None
            
    except Exception as e:
        print(f"[Supabase 로깅 에러 발생]: {e}")
        # 진짜 에러가 났을 때는 무한 재시도를 막기 위해 대기열을 비웁니다.
        st.session_state.pending_log = None


# --- 4. 화면 출력 로직 (버튼 상태와 완전히 독립됨) ---
if st.session_state.is_analyzed and st.session_state.car_data:
    
    current_car = st.session_state.saved_target_car
    current_price = st.session_state.saved_new_car_price
    
    # 💡 [핵심] 여기에 있던 last_logged_search 관련 if문과 
    # log_app_usage 관련 try-except 블록을 모조리 삭제했습니다!
    
    # --- 여기서부터는 기존 화면 출력 로직 그대로 진행 ---
    st.success("네트워크 날치기 성공! 데이터를 화면에 출력합니다.")
    
    df = pd.DataFrame(st.session_state.car_data)
    df.index = range(1, len(df) + 1)
    
    total_count = len(df)
    avg_used_price = df["매물 가격 (만 원)"].mean()
    
    if current_price > 0:
        retention_rate = (avg_used_price / current_price) * 100
        depreciation_rate = 100 - retention_rate
    else:
        retention_rate = 0
        depreciation_rate = 0

    # --- 시각적 결과 출력 ---
    col1, col2, col3 = st.columns(3)
    
    col1.metric(label="분석된 직영 매물 수", value=f"{total_count} 대")
    col2.metric(label="평균 중고 시세", value=f"{avg_used_price:,.0f} 만 원")
    
    retention_color = "normal" if retention_rate >= 70 else "inverse"
    col3.metric(
        label="가치 보존율 (감가 방어율)", 
        value=f"{retention_rate:.1f} %",
        delta=f"감가율 -{depreciation_rate:.1f}%",
        delta_color=retention_color
    )
    
    st.divider()
    
    st.subheader("📋 수집된 가격 데이터 원본 (Raw Data)")
    st.dataframe(df, use_container_width=True)

    st.subheader("📊 개별 매물 가격 비교")
    
    chart_df = df.copy()
    chart_df.index = [f"{i+1}번 차량" for i in range(len(chart_df))]
    st.bar_chart(chart_df["매물 가격 (만 원)"])

    # --- 엑셀 다운로드 기능 ---
    st.divider() 
    st.subheader("💾 데이터 내보내기")
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='중고차_시세_데이터')
    
    st.download_button(
        label="📥 엑셀 파일로 결과 다운로드",
        data=buffer.getvalue(),
        file_name=f"{current_car}_중고차_시세.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )

# --- 4. 백그라운드 로깅 전용 처리기 (파일의 가장 마지막에 배치) ---
if st.session_state.current_log_task:
    task = st.session_state.current_log_task
    task_id = task["id"]
    
    # 이 주문 번호가 아직 완료 장부에 없다면? (DB 저장을 시도합니다)
    if task_id not in st.session_state.completed_logs:
        try:
            is_logged = log_app_usage(
                "Kcar_crawler", 
                "click_analyze", 
                {"car": task["car"], "price": task["price"]}
            )
            
            # 결과가 False(LOADING 중)만 아니라면? 
            # 성공이든, 위치 API가 뻗어서 Unknown이 뜨든 일단 도장을 쾅 찍고 끝냅니다!
            if is_logged is not False:
                st.session_state.completed_logs.add(task_id)
                st.session_state.current_log_task = None  # 대기열 비우기
                
        except Exception as e:
            print(f"[Supabase 로깅 에러 발생]: {e}")
            # 진짜 에러가 났을 때도 무한 재시도를 막기 위해 작업은 완료 처리합니다.
            st.session_state.completed_logs.add(task_id)
            st.session_state.current_log_task = None
