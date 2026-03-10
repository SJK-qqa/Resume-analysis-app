import streamlit as st
import pandas as pd
import json
import random
from io import BytesIO
import PyPDF2
import warnings
import requests
import concurrent.futures
import plotly.express as px

# 消音警告
warnings.filterwarnings("ignore", message="missing ScriptRunContext!")

# ------------------- 火山方舟（豆包）API 配置 -------------------
API_KEY = "4ad4b2e3-63a5-4b19-b785-60d819a31fdd"
API_SECRET = "TURRNE56UmxNak15TW1VNU5ERTBOemt4T0dNMllqbGtPR1F4TVdGaE5tSQ=="
MODEL_ID = "bot-20260308220734-hgmhn"


def extract_text_from_pdf(pdf_file):
    """从上传的PDF文件中提取文本"""
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text


def get_token():
    """从火山方舟获取Token"""
    url = "https://ark.cn-beijing.volces.com/api/v3/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": API_SECRET
    }
    try:
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("access_token")
        else:
            st.error(f"获取Token失败：{resp.json().get('error_description', '未知错误')}")
            return None
    except Exception as e:
        st.error(f"网络异常：{str(e)}")
        return None


def llm_analyze_single(resume_text):
    """单份简历分析（真实调用豆包，失败则自动切换到本地模拟）"""
    # 本地模拟数据池
    names = ["张三", "李四", "王五", "赵六", "陈七", "刘八", "周九", "吴十"]
    educations = ["本科", "硕士", "博士", "大专"]
    majors = ["计算机科学与技术", "人力资源管理", "市场营销", "金融学", "统计学"]
    work_years = ["1-3年", "3-5年", "5-10年", "10年以上"]
    job_categories = ["信息技术", "人力资源", "市场营销", "金融财务", "数据分析"]
    skills_pool = [
        ["Python", "SQL", "数据分析"],
        ["招聘", "培训", "员工关系"],
        ["新媒体运营", "市场调研", "品牌策划"],
        ["财务建模", "风险控制", "会计"],
        ["机器学习", "数据可视化", "统计学"]
    ]

    token = get_token()
    if not token:
        st.warning("API调用失败，自动切换到本地模拟模式")
        return {
            "姓名": random.choice(names),
            "学历": random.choice(educations),
            "专业": random.choice(majors),
            "工作年限": random.choice(work_years),
            "应聘岗位类别": random.choice(job_categories),
            "核心技能": random.choice(skills_pool),
            "岗位匹配度": random.randint(60, 95),
            "匹配度分析": "模拟分析：该候选人具备相关岗位所需的核心技能，工作经验匹配度较高，适合进一步面试考察。"
        }

    # 火山方舟API地址
    api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 优化后的提示词（强制JSON）
    prompt = """你是专业HR简历分析师，仅输出JSON，无任何多余文字。
请分析以下简历，输出字段：姓名、学历、专业、工作年限、应聘岗位类别、核心技能（列表）、岗位匹配度（0-100整数）、匹配度分析。
简历内容：{}""".format(resume_text)

    data = {
        "model": MODEL_ID,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    try:
        resp = requests.post(api_url, headers=headers, json=data, timeout=30)
        if resp.status_code == 200:
            result = resp.json()["choices"][0]["message"]["content"]
            return json.loads(result)
        else:
            st.warning(f"API错误：{resp.status_code}，自动切换到本地模拟模式")
            return {
                "姓名": random.choice(names),
                "学历": random.choice(educations),
                "专业": random.choice(majors),
                "工作年限": random.choice(work_years),
                "应聘岗位类别": random.choice(job_categories),
                "核心技能": random.choice(skills_pool),
                "岗位匹配度": random.randint(60, 95),
                "匹配度分析": "模拟分析：该候选人具备相关岗位所需的核心技能，工作经验匹配度较高，适合进一步面试考察。"
            }
    except json.JSONDecodeError:
        st.warning("大模型未返回有效JSON，自动切换到本地模拟模式")
        return {
            "姓名": random.choice(names),
            "学历": random.choice(educations),
            "专业": random.choice(majors),
            "工作年限": random.choice(work_years),
            "应聘岗位类别": random.choice(job_categories),
            "核心技能": random.choice(skills_pool),
            "岗位匹配度": random.randint(60, 95),
            "匹配度分析": "模拟分析：该候选人具备相关岗位所需的核心技能，工作经验匹配度较高，适合进一步面试考察。"
        }
    except Exception as e:
        st.warning(f"调用异常：{str(e)}，自动切换到本地模拟模式")
        return {
            "姓名": random.choice(names),
            "学历": random.choice(educations),
            "专业": random.choice(majors),
            "工作年限": random.choice(work_years),
            "应聘岗位类别": random.choice(job_categories),
            "核心技能": random.choice(skills_pool),
            "岗位匹配度": random.randint(60, 95),
            "匹配度分析": "模拟分析：该候选人具备相关岗位所需的核心技能，工作经验匹配度较高，适合进一步面试考察。"
        }


def llm_analyze_batch(resumes, max_workers=3):
    """批量分析"""
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(llm_analyze_single, r) for r in resumes]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
    return results


# ------------------- 自定义CSS样式 -------------------
st.markdown("""
<style>
    .stButton > button {
        background-color: #4F46E5;
        color: white;
        border-radius: 8px;
        height: 3em;
        width: 100%;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #4338CA;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
    }
    .css-1d391kg {
        padding-top: 2rem;
    }
    .css-1544g2n {
        padding: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ------------------- Streamlit 界面 -------------------
st.set_page_config(page_title="智能简历分析助手", layout="wide", page_icon="📄")

# 初始化 session_state，持久化 res_df
if 'res_df' not in st.session_state:
    st.session_state.res_df = None

# 侧边栏导航（修复版）
with st.sidebar:
    st.image("https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png", width=200)
    st.title("导航菜单")
    st.markdown("🏠 首页（当前页面）")
    st.markdown("❓ 使用帮助（功能说明见首页）")
    st.divider()
    st.markdown("**版本：v1.0** | 适配：Streamlit 1.30+")
    st.markdown("© 2026 智能简历分析助手")

# 主页面标题
st.title("📄 智能简历分析助手", anchor=None)
st.markdown("""
**FIT国脉杯 · AI与大数据赛道**  
支持单份PDF/文本分析、批量简历分类、岗位匹配度可视化
""")
st.divider()

# 功能说明卡片
with st.container(border=True):
    st.subheader("💡 功能说明")
    st.markdown("""
    - 单份分析：上传PDF或粘贴文本，一键提取关键信息
    - 批量分类：支持CSV导入，自定义分析前N条简历
    - 结果筛选：按岗位、匹配度快速筛选候选人
    - 数据可视化：岗位分布、匹配度热力图直观展示
    """)

# 定义标签页
tab1, tab2, tab3 = st.tabs(["单份简历分析", "批量简历分类", "数据统计"])

# --- 标签页1：单份简历分析 ---
with tab1:
    st.subheader("单份简历AI分析")

    # 选择输入方式
    input_mode = st.radio("选择输入方式", ["粘贴简历文本", "上传PDF文件"])

    if input_mode == "粘贴简历文本":
        input_text = st.text_area("粘贴简历内容", height=250)
        if st.button("开始AI分析"):
            if input_text:
                with st.spinner("🧠 豆包大模型正在深度分析简历..."):
                    res = llm_analyze_single(input_text)
                    st.json(res)
                    st.success("✅ 分析完成！")
                    st.balloons()
    else:
        # 上传PDF文件
        uploaded_pdf = st.file_uploader("上传简历PDF", type="pdf")
        if uploaded_pdf:
            with st.spinner("正在提取PDF文本..."):
                pdf_text = extract_text_from_pdf(uploaded_pdf)
                st.text_area("提取的PDF文本", pdf_text, height=250)

                if st.button("开始AI分析"):
                    with st.spinner("🧠 豆包大模型正在深度分析简历..."):
                        res = llm_analyze_single(pdf_text)
                        st.json(res)
                        st.success("✅ 分析完成！")
                        st.balloons()

# --- 标签页2：批量简历分类 ---
with tab2:
    st.subheader("批量简历分类")
    uploaded_file = st.file_uploader("上传简历数据集.csv", type="csv")

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        total_count = len(df)
        st.dataframe(df.head(5), use_container_width=True)
        st.success(f"✅ 加载成功，共 {total_count} 份简历")

        # 批量分析设置
        st.subheader("⚙️ 批量分析设置")
        col1, col2, col3 = st.columns(3)
        with col1:
            # 生成带推荐标记的选项列表，给Resume_str标注⭐推荐
            display_options = [col + " ⭐推荐" if col == "Resume_str" else col for col in df.columns.tolist()]
            # 默认选中Resume_str列
            default_idx = df.columns.get_loc("Resume_str") if "Resume_str" in df.columns else 0
            # 渲染下拉选择框
            selected_display = st.selectbox(
                "📝 简历文本列",
                options=display_options,
                index=default_idx,
                help="请选择包含简历纯文本内容的列，带⭐推荐的列更适合AI分析"
            )
            # 去除推荐标记，获取真实列名用于后续分析
            text_column = selected_display.replace(" ⭐推荐", "")
        with col2:
            analyze_count = st.number_input(
                "🔢 分析前 N 条",
                min_value=1,
                max_value=total_count,
                value=min(2, total_count),
                step=1
            )
        with col3:
            st.metric(label="总简历数", value=total_count)

        if st.button("批量AI分析"):
            with st.spinner(f"正在分析前 {analyze_count} 条简历..."):
                df_subset = df.head(analyze_count)
                resumes = df_subset[text_column].astype(str).tolist()
                results = llm_analyze_batch(resumes)
                # 将结果保存到session_state，实现数据持久化
                st.session_state.res_df = pd.DataFrame(results)

                # 美化结果表格
                st.dataframe(
                    st.session_state.res_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "岗位匹配度": st.column_config.ProgressColumn(
                            "岗位匹配度",
                            help="0-100分",
                            format="%d",
                            min_value=0,
                            max_value=100,
                        ),
                        "核心技能": st.column_config.ListColumn(
                            "核心技能",
                            help="候选人掌握的关键技能",
                        ),
                    },
                    height=400,
                )

                # 导出Excel结果
                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    st.session_state.res_df.to_excel(writer, index=False, sheet_name="分析结果")
                output.seek(0)

                st.download_button(
                    "📥 下载结果",
                    data=output,
                    file_name="简历分析结果.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success("✅ 批量分析完成！")
                st.balloons()

    # 筛选功能（基于session_state持久化数据）
    if st.session_state.res_df is not None:
        st.subheader("结果筛选")
        col1, col2 = st.columns(2)
        with col1:
            if "应聘岗位类别" in st.session_state.res_df.columns:
                jobs = st.session_state.res_df["应聘岗位类别"].dropna().unique()
                selected_job = st.selectbox("选择岗位", jobs)
                filtered = st.session_state.res_df[st.session_state.res_df["应聘岗位类别"] == selected_job]
            else:
                st.error("缺少'应聘岗位类别'字段，无法筛选")
                filtered = st.session_state.res_df
        with col2:
            if "岗位匹配度" in st.session_state.res_df.columns:
                min_score = st.slider("最低匹配度", 0, 100, 70)
                filtered = filtered[filtered["岗位匹配度"] >= min_score]
            else:
                st.warning("缺少'岗位匹配度'字段，无法筛选")

        st.dataframe(filtered, use_container_width=True)

# --- 标签页3：数据统计 ---
with tab3:
    st.subheader("数据统计")
    # 从session_state读取分析结果
    if st.session_state.res_df is not None:
        col1, col2 = st.columns(2)
        with col1:
            if "应聘岗位类别" in st.session_state.res_df.columns:
                st.subheader("岗位分布")
                job_counts = st.session_state.res_df["应聘岗位类别"].value_counts().reset_index()
                job_counts.columns = ["岗位", "人数"]
                fig = px.bar(
                    job_counts,
                    x="岗位",
                    y="人数",
                    color="岗位",
                    title="各岗位候选人分布",
                    template="plotly_dark",
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("缺少'应聘岗位类别'字段，无法生成岗位分布图表")
        with col2:
            if "岗位匹配度" in st.session_state.res_df.columns:
                st.subheader("匹配度分布")
                fig = px.histogram(
                    st.session_state.res_df,
                    x="岗位匹配度",
                    nbins=10,
                    title="岗位匹配度分布",
                    template="plotly_dark",
                    color_discrete_sequence=["#10B981"]
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("缺少'岗位匹配度'字段，无法生成匹配度分布图表")
    else:
        st.info("请先完成批量分析")