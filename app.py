import os
import streamlit as st
import pandas as pd
import numpy as np
from neo4j import GraphDatabase

# ================= 页面基础配置 =================
st.set_page_config(
    page_title="牛肉贸易摩擦 SPS 反制量化推演原型系统",
    page_icon="🥩",
    layout="wide"
)

def _cfg(k, default=""):
    try:
        if k in st.secrets and str(st.secrets[k]).strip():
            return str(st.secrets[k]).strip()
    except Exception:
        pass
    val = os.getenv(k, default)
    return str(val).strip() if val is not None else default

NEO4J_URI = _cfg("NEO4J_URI", "neo4j+s://d467745a.databases.neo4j.io")
NEO4J_USER = _cfg("NEO4J_USER") or _cfg("NEO4J_USERNAME", "d467745a")
NEO4J_PASS = _cfg("NEO4J_PASS") or _cfg("NEO4J_PASSWORD", "")

@st.cache_resource
def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

def run_cypher(query, params=None):
    driver = get_driver()
    with driver.session() as session:
        return session.run(query, params or {}).data()

# ================= 侧边栏导航 =================
st.sidebar.title("🥩 SPS 知识图谱与反制推演")
st.sidebar.markdown("**底座引擎**：Neo4j 5.26 图数据库")
page = st.sidebar.radio(
    "选择功能模块",
    ["1. 图谱全景与实证基准库", "2. 自然语言智能检索 (GraphQA)", "3. SPS 反制工具量化推演沙盘"]
)

# ================= 模块 1：图谱全景与实证基准库 =================
if page == "1. 图谱全景与实证基准库":
    st.title("📊 牛肉贸易摩擦 SPS 知识图谱全景看板")

    counts_rows = run_cypher("""
        MATCH (n:SPS_Measure) WITH count(n) AS m_cnt
        MATCH (d:Dispute) WITH m_cnt, count(d) AS d_cnt
        MATCH (c:Country) WITH m_cnt, d_cnt, count(c) AS c_cnt
        MATCH ()-[r:TRIGGERS]->() RETURN m_cnt, d_cnt, c_cnt, count(r) AS link_cnt
    """)
    counts = counts_rows[0] if counts_rows else {"m_cnt": 0, "d_cnt": 0, "c_cnt": 0, "link_cnt": 0}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("纯净涉牛肉 SPS 通报", f"{counts['m_cnt']} 条")
    c2.metric("WTO 争端与特别关注", f"{counts['d_cnt']} 起")
    c3.metric("覆盖贸易成员国/地区", f"{counts['c_cnt']} 个")
    c4.metric("通报-争端跨表触发边", f"{counts['link_cnt']} 条")

    st.divider()
    col_left, col_right = st.columns([1.15, 1])

    with col_left:
        st.subheader("六大 SPS 措施维度分布与实证弹性参数（表三）")
        cat_data = run_cypher("""
            MATCH (m:SPS_Measure)-[:BELONGS_TO]->(cat:Measure_Category)-[:HAS_ELASTICITY]->(emp:Empirical_Elasticity)
            OPTIONAL MATCH (m)-[:TRIGGERS]->(d:Dispute)
            RETURN cat.name AS 措施维度,
                   count(DISTINCT m) AS 通报数量,
                   count(DISTINCT d) AS 关联争端数,
                   emp.ave_pct AS 实证AVE_pct,
                   emp.import_elasticity AS 进口价格弹性,
                   emp.trade_drop_pct AS 短期贸易抑制率_pct
            ORDER BY 通报数量 DESC
        """)
        df_cat = pd.DataFrame(cat_data)
        st.dataframe(df_cat, width="stretch", hide_index=True)

        if not df_cat.empty:
            st.download_button(
                label="⬇️ 导出六大维度实证参数表 (CSV)",
                data=df_cat.to_csv(index=False).encode("utf-8-sig"),
                file_name="sps_six_dimensions_empirical_table3.csv",
                mime="text/csv"
            )

    with col_right:
        st.subheader("各类 SPS 工具贸易抑制强度对比 (AVE %)")
        if not df_cat.empty:
            st.bar_chart(
                df_cat.set_index("措施维度")[["实证AVE_pct", "短期贸易抑制率_pct"]],
                stack=False,
                width="stretch"
            )

    with st.expander("📖 看板指标与实证参数口径说明"):
        st.markdown("""
        * **纯净涉牛肉 SPS 通报**：经清洗筛选后的涉牛肉卫生与植物检疫措施通报总数。
        * **WTO 争端与特别关注**：与涉牛肉贸易摩擦相关的正式争端（DS）及特别贸易关注（STC）记录数。
        * **实证 AVE（Ad Valorem Equivalent, %）**：将非关税 SPS 监管壁垒折算为等价从价关税率的实证基准值。
        * **短期贸易抑制率（%）**：对应措施维度在实证基准下的短期双边贸易额下降幅度。
        """)

# ================= 模块 2：自然语言智能检索 =================
elif page == "2. 自然语言智能检索 (GraphQA)":
    st.title("🔍 牛肉 SPS 知识图谱自然语言智能检索")
    st.caption("内置 154 个成员中英文/代码映射 + 复合国家名单精确拆解 + 争端自动回溯，支持多维筛选与全字段导出。")

    FULL_COUNTRY_MAP = {
        "阿富汗": ["AFG", "Afghanistan"], "阿尔巴尼亚": ["ALB", "Albania"], "阿尔及利亚": ["DZA", "Algeria"],
        "安哥拉": ["AGO", "Angola"], "安提瓜和巴布达": ["ATG", "Antigua and Barbuda"], "阿根廷": ["ARG", "Argentina"],
        "亚美尼亚": ["ARM", "Armenia"], "澳大利亚": ["AUS", "Australia"], "奥地利": ["AUT", "Austria"],
        "阿塞拜疆": ["AZE", "Azerbaijan"], "巴哈马": ["BHS", "Bahamas"], "巴林": ["BHR", "Bahrain"],
        "孟加拉国": ["BGD", "Bangladesh"], "巴巴多斯": ["BRB", "Barbados"], "白俄罗斯": ["BLR", "Belarus"],
        "比利时": ["BEL", "Belgium"], "伯利兹": ["BLZ", "Belize"], "贝宁": ["BEN", "Benin"],
        "不丹": ["BTN", "Bhutan"], "玻利维亚": ["BOL", "Bolivia"], "波黑": ["BIH", "Bosnia and Herzegovina"],
        "博茨瓦纳": ["BWA", "Botswana"], "巴西": ["BRA", "Brazil"], "文莱": ["BRN", "Brunei"],
        "保加利亚": ["BGR", "Bulgaria"], "布基纳法索": ["BFA", "Burkina Faso"], "布隆迪": ["BDI", "Burundi"],
        "柬埔寨": ["KHM", "Cambodia"], "喀麦隆": ["CMR", "Cameroon"], "加拿大": ["CAN", "Canada"],
        "佛得角": ["CPV", "Cabo Verde", "Cape Verde"], "中非": ["CAF", "Central African Republic"], "乍得": ["TCD", "Chad"],
        "智利": ["CHL", "Chile"], "中国": ["CHN", "China"], "中国香港": ["HKG", "Hong Kong"],
        "中国澳门": ["MAC", "Macao", "Macau"], "中国台湾": ["TPKM", "Chinese Taipei", "Taiwan"],
        "哥伦比亚": ["COL", "Colombia"], "科摩罗": ["COM", "Comoros"], "刚果布": ["COG", "Congo"],
        "刚果金": ["COD", "Democratic Republic of the Congo"], "哥斯达黎加": ["CRI", "Costa Rica"],
        "科特迪瓦": ["CIV", "Côte d'Ivoire", "Cote d'Ivoire"], "克罗地亚": ["HRV", "Croatia"], "古巴": ["CUB", "Cuba"],
        "塞浦路斯": ["CYP", "Cyprus"], "捷克": ["CZE", "Czechia", "Czech Republic"], "丹麦": ["DNK", "Denmark"],
        "吉布提": ["DJI", "Djibouti"], "多米尼克": ["DMA", "Dominica"], "多米尼加": ["DOM", "Dominican Republic"],
        "厄瓜多尔": ["ECU", "Ecuador"], "埃及": ["EGY", "Egypt"], "萨尔瓦多": ["SLV", "El Salvador"],
        "赤道几内亚": ["GNQ", "Equatorial Guinea"], "厄立特里亚": ["ERI", "Eritrea"], "爱沙尼亚": ["EST", "Estonia"],
        "斯威士兰": ["SWZ", "Eswatini", "Swaziland"], "埃塞俄比亚": ["ETH", "Ethiopia"], "欧盟": ["EUR", "European Union", "European"],
        "斐济": ["FJI", "Fiji"], "芬兰": ["FIN", "Finland"], "法国": ["FRA", "France"],
        "加蓬": ["GAB", "Gabon"], "冈比亚": ["GMB", "Gambia"], "格鲁吉亚": ["GEO", "Georgia"],
        "德国": ["DEU", "Germany"], "加纳": ["GHA", "Ghana"], "希腊": ["GRC", "Greece"],
        "格林纳达": ["GRD", "Grenada"], "危地马拉": ["GTM", "Guatemala"], "几内亚": ["GIN", "Guinea"],
        "几内亚比绍": ["GNB", "Guinea-Bissau"], "圭亚那": ["GUY", "Guyana"], "海地": ["HTI", "Haiti"],
        "洪都拉斯": ["HND", "Honduras"], "匈牙利": ["HUN", "Hungary"], "冰岛": ["ISL", "Iceland"],
        "印度": ["IND", "India"], "印度尼西亚": ["IDN", "Indonesia"], "伊朗": ["IRN", "Iran"],
        "伊拉克": ["IRQ", "Iraq"], "爱尔兰": ["IRL", "Ireland"], "以色列": ["ISR", "Israel"],
        "意大利": ["ITA", "Italy"], "牙买加": ["JAM", "Jamaica"], "日本": ["JPN", "Japan"],
        "约旦": ["JOR", "Jordan"], "哈萨克斯坦": ["KAZ", "Kazakhstan"], "肯尼亚": ["KEN", "Kenya"],
        "韩国": ["KOR", "Korea", "Republic of Korea", "Korea, Republic of"],
        "科威特": ["KWT", "Kuwait"], "吉尔吉斯斯坦": ["KGZ", "Kyrgyzstan"],
        "老挝": ["LAO", "Lao", "Laos"], "拉脱维亚": ["LVA", "Latvia"], "黎巴嫩": ["LBN", "Lebanon"],
        "莱索托": ["LSO", "Lesotho"], "利比里亚": ["LBR", "Liberia"], "利比亚": ["LBY", "Libya"],
        "列支敦士登": ["LIE", "Liechtenstein"], "立陶宛": ["LTU", "Lithuania"], "卢森堡": ["LUX", "Luxembourg"],
        "马达加斯加": ["MDG", "Madagascar"], "马拉维": ["MWI", "Malawi"], "马来西亚": ["MYS", "Malaysia"],
        "马尔代夫": ["MDV", "Maldives"], "马里": ["MLI", "Mali"], "马耳他": ["MLT", "Malta"],
        "毛里塔尼亚": ["MRT", "Mauritania"], "毛里求斯": ["MUS", "Mauritius"], "墨西哥": ["MEX", "Mexico"],
        "摩尔多瓦": ["MDA", "Moldova"], "蒙古": ["MNG", "Mongolia"], "黑山": ["MNE", "Montenegro"],
        "摩洛哥": ["MAR", "Morocco"], "莫桑比克": ["MOZ", "Mozambique"], "缅甸": ["MMR", "Myanmar", "Burma"],
        "纳米比亚": ["NAM", "Namibia"], "尼泊尔": ["NPL", "Nepal"], "荷兰": ["NLD", "Netherlands"],
        "新西兰": ["NZL", "New Zealand"], "尼加拉瓜": ["NIC", "Nicaragua"], "尼日尔": ["NER", "Niger"],
        "尼日利亚": ["NGA", "Nigeria"], "北马其顿": ["MKD", "North Macedonia"], "挪威": ["NOR", "Norway"],
        "阿曼": ["OMN", "Oman"], "巴基斯坦": ["PAK", "Pakistan"], "巴拿马": ["PAN", "Panama"],
        "巴布亚新几内亚": ["PNG", "Papua New Guinea"], "巴拉圭": ["PRY", "Paraguay"], "秘鲁": ["PER", "Peru"],
        "菲律宾": ["PHL", "Philippines"], "波兰": ["POL", "Poland"], "葡萄牙": ["PRT", "Portugal"],
        "卡塔尔": ["QAT", "Qatar"], "罗马尼亚": ["ROU", "Romania"], "俄罗斯": ["RUS", "Russian", "Russia", "Russian Federation"],
        "卢旺达": ["RWA", "Rwanda"], "圣基茨和尼维斯": ["KNA", "Saint Kitts and Nevis"], "圣卢西亚": ["LCA", "Saint Lucia"],
        "圣文森特和格林纳丁斯": ["VCT", "Saint Vincent and the Grenadines"], "萨摩亚": ["WSM", "Samoa"],
        "沙特": ["SAU", "Saudi Arabia"], "塞内加尔": ["SEN", "Senegal"], "塞尔维亚": ["SRB", "Serbia"],
        "塞舌尔": ["SYC", "Seychelles"], "塞拉利昂": ["SLE", "Sierra Leone"], "新加坡": ["SGP", "Singapore"],
        "斯洛伐克": ["SVK", "Slovakia"], "斯洛文尼亚": ["SVN", "Slovenia"], "所罗门群岛": ["SLB", "Solomon Islands"],
        "南非": ["ZAF", "South Africa"], "西班牙": ["ESP", "Spain"], "斯里兰卡": ["LKA", "Sri Lanka"],
        "苏里南": ["SUR", "Suriname"], "瑞典": ["SWE", "Sweden"], "瑞士": ["CHE", "Switzerland"],
        "塔吉克斯坦": ["TJK", "Tajikistan"], "坦桑尼亚": ["TZA", "Tanzania"], "泰国": ["THA", "Thailand", "Kingdom of Thailand"],
        "多哥": ["TGO", "Togo"], "汤加": ["TON", "Tonga"], "特立尼达和多巴哥": ["TTO", "Trinidad and Tobago"],
        "突尼斯": ["TUN", "Tunisia"], "土耳其": ["TUR", "Türkiye", "Turkey"], "乌干达": ["UGA", "Uganda"],
        "乌克兰": ["UKR", "Ukraine"], "阿联酋": ["ARE", "United Arab Emirates"], "英国": ["GBR", "United Kingdom"],
        "美国": ["USA", "United States", "United States of America"], "乌拉圭": ["URY", "Uruguay"], "乌兹别克斯坦": ["UZB", "Uzbekistan"],
        "瓦努阿图": ["VUT", "Vanuatu"], "委内瑞拉": ["VEN", "Venezuela"], "越南": ["VNM", "Viet Nam", "Vietnam"],
        "也门": ["YEM", "Yemen"], "赞比亚": ["ZMB", "Zambia"], "津巴布韦": ["ZWE", "Zimbabwe"]
    }

    def build_exact_country_filter(field_expr, tokens):
        tok_list = sorted({
            t.strip().upper().replace("'", "\\'")
            for t in tokens
            if t and len(t.strip()) >= 2
        })
        if not tok_list:
            return "false"
        tok_array_str = "[" + ", ".join([f"'{x}'" for x in tok_list]) + "]"
        return (
            f"any(part IN [p IN split(toUpper(coalesce({field_expr}, '')), ',') | trim(p)] "
            f"WHERE part IN {tok_array_str})"
        )

    link_cfg = {"原文链接": st.column_config.LinkColumn("原文链接", display_text="打开WTO原文")}
    tab_nl, tab_combo = st.tabs(["💬 自然语言智能问答（154国全覆盖）", "🎛️ 全库成员实体多维筛选（10字段）"])

    with tab_nl:
        preset = st.selectbox(
            "快捷示例问题（也可在下方文本框自由输入任意国家与措施）：",
            [
                "查询巴拿马（Panama）相关的牛肉 SPS 通报与争端",
                "查询触发过 WTO 争端（STC）的牛肉 SPS 通报完整证据链",
                "查询美国（USA）发布的牛肉疫病检疫类 SPS 通报",
                "查询巴西（BRA）发布的牛肉 SPS 通报",
                "查询澳大利亚（AUS）发布的牛肉 SPS 通报",
                "查询历史提出频次最高（Times_Raised >= 4）的涉牛肉 WTO 特别贸易关注"
            ]
        )
        user_q = st.text_input("输入自定义检索问题（支持任意国家中英文名、ISO3 代码或措施关键词）：", value=preset)

        if st.button("执行图谱穿透检索", type="primary"):
            matched_labels = []
            target_tokens = []

            for cn_name, aliases in FULL_COUNTRY_MAP.items():
                if cn_name in user_q or any(
                    (len(a) == 3 and a.isalpha() and f" {a.upper()} " in f" {user_q.upper()} ")
                    or (len(a) > 3 and a.upper() in user_q.upper())
                    for a in aliases
                ):
                    matched_labels.append(cn_name)
                    target_tokens.extend(aliases)

            if not target_tokens:
                db_countries = [r["name"] for r in run_cypher("MATCH (c:Country) RETURN DISTINCT c.iso3 AS name") if r["name"]]
                for dc in db_countries:
                    dc_clean = dc.strip()
                    if len(dc_clean) == 3 and dc_clean.isalpha():
                        if f" {dc_clean.upper()} " in f" {user_q.upper()} ":
                            matched_labels.append(dc_clean)
                            target_tokens.append(dc_clean)
                    elif len(dc_clean) >= 4 and dc_clean.upper() in user_q.upper():
                        matched_labels.append(dc_clean)
                        target_tokens.append(dc_clean)

            cats = ["疫病检疫", "兽药残留", "注册资质", "区域化管理", "检测认证", "包装追溯"]
            matched_cats = [c for c in cats if c in user_q]

            if matched_labels:
                st.caption(f"已识别检索目标国家/地区：**{'、'.join(dict.fromkeys(matched_labels))}**")

            if "频次最高" in user_q or "Times_Raised" in user_q or ("特别贸易关注" in user_q and "通报" not in user_q and not target_tokens):
                cypher = """
                MATCH (comp:Country)-[:RAISES_CONCERN]->(d:Dispute)-[:AGAINST_RESPONDENT]->(resp:Country)
                WHERE d.times_raised >= 4
                OPTIONAL MATCH (trig_m:SPS_Measure)-[:TRIGGERS]->(d)
                RETURN d.dispute_id AS 争端编号, d.dispute_type AS 争端类型, d.raised_year AS 首次提出年份,
                       d.times_raised AS 累计磋商频次, collect(DISTINCT comp.iso3) AS 起诉方,
                       collect(DISTINCT resp.iso3) AS 被诉方, collect(DISTINCT trig_m.measure_id) AS 关联涉案通报,
                       d.core_issue AS 核心争议焦点
                ORDER BY d.times_raised DESC LIMIT 30
                """
                res = run_cypher(cypher)
                with st.expander("查看自动生成的 Cypher 图查询语句"):
                    st.text(cypher)
                if res:
                    st.success(f"检索成功！共命中 {len(res)} 条高频争端/关注记录：")
                    st.dataframe(pd.DataFrame(res), width="stretch", hide_index=True)
                else:
                    st.info("当前图谱中暂无累计磋商频次 >= 4 的记录。")

            elif "触发" in user_q or "证据链" in user_q or ("争端" in user_q and not target_tokens and not matched_cats):
                cypher = """
                MATCH (c:Country)-[:NOTIFIES]->(m:SPS_Measure)-[:TRIGGERS]->(d:Dispute)
                OPTIONAL MATCH (m)-[:BELONGS_TO]->(cat:Measure_Category)-[:HAS_ELASTICITY]->(emp:Empirical_Elasticity)
                OPTIONAL MATCH (m)-[:TARGETS]->(t:Country)
                RETURN c.iso3 AS 通报发布国, m.measure_id AS 通报编号, m.publish_date AS 发布日期,
                       m.is_emergency AS 是否紧急通报, collect(DISTINCT cat.name) AS 措施分类,
                       max(emp.ave_pct) AS 最高实证AVE_pct, d.dispute_id AS 关联WTO争端,
                       collect(DISTINCT t.iso3) AS 受影响成员, m.title AS 通报标题, m.source_link AS 原文链接
                LIMIT 50
                """
                res = run_cypher(cypher)
                with st.expander("查看自动生成的 Cypher 图查询语句"):
                    st.text(cypher)
                if res:
                    st.success(f"检索成功！共命中 {len(res)} 条触发争端的通报记录：")
                    st.dataframe(pd.DataFrame(res), width="stretch", hide_index=True, column_config=link_cfg)
                else:
                    st.info("当前图谱中暂无触发争端的通报记录。")

            else:
                if not target_tokens and not matched_cats:
                    st.warning("未能识别出有效的国家名称或措施维度，请尝试输入国家中英文名（如 巴拿马 / Panama / 韩国 / 泰国）、ISO3 代码，或在右侧【全库成员实体多维筛选】中直接选择。")
                    st.stop()

                c_cond = build_exact_country_filter("c.iso3", target_tokens) if target_tokens else "true"
                cat_filter_clause = ""
                if matched_cats:
                    cat_list_str = "[" + ", ".join([f"'{c}'" for c in matched_cats]) + "]"
                    cat_filter_clause = f"WHERE cat.name IN {cat_list_str}"

                cypher = f"""
                MATCH (c:Country)-[:NOTIFIES]->(m:SPS_Measure)
                WHERE {c_cond}
                OPTIONAL MATCH (m)-[:BELONGS_TO]->(cat:Measure_Category)-[:HAS_ELASTICITY]->(emp:Empirical_Elasticity)
                {cat_filter_clause}
                OPTIONAL MATCH (m)-[:TRIGGERS]->(d:Dispute)
                OPTIONAL MATCH (m)-[:TARGETS]->(t:Country)
                RETURN DISTINCT c.iso3 AS 通报发布国,
                       m.measure_id AS 通报编号,
                       m.publish_date AS 发布日期,
                       m.is_emergency AS 是否紧急通报,
                       collect(DISTINCT cat.name) AS 措施分类,
                       max(emp.ave_pct) AS 最高实证AVE_pct,
                       collect(DISTINCT d.dispute_id) AS 关联WTO争端,
                       collect(DISTINCT t.iso3) AS 受影响成员,
                       m.title AS 通报标题,
                       m.source_link AS 原文链接
                ORDER BY m.publish_date DESC LIMIT 50
                """

                with st.expander("查看自动生成的 Cypher 图查询语句"):
                    st.text(cypher)

                res = run_cypher(cypher)
                if res:
                    st.success(f"检索成功！共命中 {len(res)} 条该国/该维度直接发布的图谱通报记录：")
                    st.dataframe(pd.DataFrame(res), width="stretch", hide_index=True, column_config=link_cfg)
                elif target_tokens:
                    comp_cond = build_exact_country_filter("comp.iso3", target_tokens)
                    resp_cond = build_exact_country_filter("resp.iso3", target_tokens)
                    disp_fallback = run_cypher(f"""
                        MATCH (comp:Country)-[:RAISES_CONCERN]->(d:Dispute)-[:AGAINST_RESPONDENT]->(resp:Country)
                        WHERE ({comp_cond}) OR ({resp_cond})
                        OPTIONAL MATCH (trig_m:SPS_Measure)-[:TRIGGERS]->(d)
                        RETURN DISTINCT d.dispute_id AS 争端编号, d.dispute_type AS 争端类型, d.raised_year AS 首次提出年份,
                               d.times_raised AS 累计磋商频次, collect(DISTINCT comp.iso3) AS 起诉方,
                               collect(DISTINCT resp.iso3) AS 被诉方, collect(DISTINCT trig_m.measure_id) AS 关联涉案通报,
                               d.core_issue AS 核心争议焦点
                    """)
                    if disp_fallback:
                        st.info(f"该成员在当前涉牛肉通报库中暂无直接发布的通报，但已精确查到其参与的 **{len(disp_fallback)}** 起相关 WTO 争端/特别贸易关注：")
                        st.dataframe(pd.DataFrame(disp_fallback), width="stretch", hide_index=True)
                    else:
                        st.info("该成员在当前涉牛肉通报库与争端库中暂无直接发布的通报或参与的争端记录。")

    with tab_combo:
        st.markdown("自动拆解图谱全部 154 个成员节点的复合名单，支持按**单个独立国家/地区**全维度穿透查询（含 10 项核心字段）：")
        raw_nodes = [r["name"] for r in run_cypher("MATCH (c:Country) RETURN DISTINCT c.iso3 AS name") if r["name"]]

        clean_countries = set()
        for item in raw_nodes:
            parts = [
                p.strip() for p in item.split(", ")
                if p.strip() and p.strip() not in [
                    "Republic of", "Islamic Republic of", "Democratic Republic of the",
                    "Plurinational State of", "Bolivarian Republic of"
                ]
            ]
            for p in parts:
                if len(p) >= 2 and "WTO成员" not in p:
                    clean_countries.add(p)
        sorted_countries = sorted(clean_countries)
        st.caption(f"拆解对齐后共覆盖 **{len(sorted_countries)}** 个独立贸易成员国/地区。")

        selected_single = st.selectbox(
            "选择任意单个国家/地区：",
            sorted_countries,
            index=sorted_countries.index("Brazil") if "Brazil" in sorted_countries else 0
        )
        if selected_single:
            single_filter_c = build_exact_country_filter("c.iso3", [selected_single])
            single_filter_comp = build_exact_country_filter("comp.iso3", [selected_single])
            single_filter_resp = build_exact_country_filter("resp.iso3", [selected_single])

            m_notify = run_cypher(f"""
                MATCH (c:Country)-[:NOTIFIES]->(m:SPS_Measure)
                WHERE {single_filter_c}
                OPTIONAL MATCH (m)-[:BELONGS_TO]->(cat:Measure_Category)-[:HAS_ELASTICITY]->(emp:Empirical_Elasticity)
                OPTIONAL MATCH (m)-[:TRIGGERS]->(d:Dispute)
                OPTIONAL MATCH (m)-[:TARGETS]->(t:Country)
                RETURN c.iso3 AS 通报发布国,
                       m.measure_id AS 通报编号,
                       m.publish_date AS 发布日期,
                       m.is_emergency AS 是否紧急通报,
                       collect(DISTINCT cat.name) AS 措施分类,
                       max(emp.ave_pct) AS 最高实证AVE_pct,
                       collect(DISTINCT d.dispute_id) AS 关联WTO争端,
                       collect(DISTINCT t.iso3) AS 受影响成员,
                       m.title AS 通报标题,
                       m.source_link AS 原文链接
                ORDER BY m.publish_date DESC LIMIT 100
            """)

            m_target = run_cypher(f"""
                MATCH (pub:Country)-[:NOTIFIES]->(m:SPS_Measure)-[:TARGETS]->(c:Country)
                WHERE {single_filter_c}
                OPTIONAL MATCH (m)-[:BELONGS_TO]->(cat:Measure_Category)-[:HAS_ELASTICITY]->(emp:Empirical_Elasticity)
                OPTIONAL MATCH (m)-[:TRIGGERS]->(d:Dispute)
                RETURN pub.iso3 AS 通报发布国,
                       m.measure_id AS 通报编号,
                       m.publish_date AS 发布日期,
                       m.is_emergency AS 是否紧急通报,
                       collect(DISTINCT cat.name) AS 措施分类,
                       max(emp.ave_pct) AS 最高实证AVE_pct,
                       collect(DISTINCT d.dispute_id) AS 关联WTO争端,
                       m.title AS 通报标题,
                       m.source_link AS 原文链接
                ORDER BY m.publish_date DESC LIMIT 100
            """)

            d_res = run_cypher(f"""
                MATCH (comp:Country)-[:RAISES_CONCERN]->(d:Dispute)-[:AGAINST_RESPONDENT]->(resp:Country)
                WHERE ({single_filter_comp}) OR ({single_filter_resp})
                OPTIONAL MATCH (trig_m:SPS_Measure)-[:TRIGGERS]->(d)
                RETURN DISTINCT d.dispute_id AS 争端编号,
                       d.dispute_type AS 争端类型,
                       d.raised_year AS 首次提出年份,
                       d.times_raised AS 累计磋商频次,
                       collect(DISTINCT comp.iso3) AS 起诉方,
                       collect(DISTINCT resp.iso3) AS 被诉方,
                       collect(DISTINCT trig_m.measure_id) AS 关联涉案通报,
                       d.core_issue AS 核心争议焦点
            """)

            c_a, c_b, c_c = st.columns(3)
            c_a.metric("主动发布 SPS 通报", f"{len(m_notify)} 条")
            c_b.metric("受他国通报影响", f"{len(m_target)} 条")
            c_c.metric("参与 WTO 争端/关注", f"{len(d_res)} 起")

            if m_notify:
                st.markdown("##### 📤 该国主动发布的牛肉 SPS 通报（全字段明细）")
                st.dataframe(pd.DataFrame(m_notify), width="stretch", hide_index=True, column_config=link_cfg)
            if m_target:
                st.markdown("##### 📥 明确点名影响该国的他国 SPS 通报（全字段明细）")
                st.dataframe(pd.DataFrame(m_target), width="stretch", hide_index=True, column_config=link_cfg)
            if d_res:
                st.markdown("##### ⚖️ 该国参与的 WTO 争端与特别贸易关注（全字段明细）")
                st.dataframe(pd.DataFrame(d_res), width="stretch", hide_index=True)
# ================= 模块 3：SPS 反制工具量化推演沙盘 =================
elif page == "3. SPS 反制工具量化推演沙盘":
    st.title("⚖️ 牛肉贸易摩擦 SPS 反制工具量化评估与推演沙盘")
    st.markdown("基于知识图谱实证参数（Kee et al. / Fontagné et al. AVE 基准）与 Armington 局部均衡替代弹性进行反制效果模拟。")

    col_cfg, col_res = st.columns([1, 1.35])

    with col_cfg:
        st.subheader("1. 设定反制情景参数")
        target_country = st.selectbox(
            "选择拟反制目标供应国",
            ["美国 (USA)", "澳大利亚 (AUS)", "欧盟 (EUR)", "巴西 (BRA)", "加拿大 (CAN)"]
        )
        base_trade = st.number_input("基准年自该国牛肉进口额（亿美元）", min_value=0.5, max_value=200.0, value=16.5, step=0.5)

        emp_rows = run_cypher("""
            MATCH (cat:Measure_Category)-[:HAS_ELASTICITY]->(emp:Empirical_Elasticity)
            RETURN cat.name AS name, emp.ave_pct AS ave, emp.import_elasticity AS elast, emp.trade_drop_pct AS drop
        """)
        emp_dict = {r["name"]: r for r in emp_rows}

        selected_tools = st.multiselect(
            "选择拟组合动用的 SPS 反制工具（可多选叠加）",
            list(emp_dict.keys()),
            default=["注册资质", "检测认证"]
        )
        intensity = st.slider("执法严格度系数（1.0 = 常规标准，1.5 = 顶格口岸严查/暂停准入）", 0.6, 1.5, 1.1, 0.1)

    with col_res:
        st.subheader("2. 量化推演评估结果")
        if not selected_tools:
            st.info("请在左侧至少选择一项 SPS 反制工具以启动推演。")
        else:
            aves = sorted([emp_dict[t]["ave"] for t in selected_tools], reverse=True)
            combined_ave = sum(a * (0.65 ** idx) for idx, a in enumerate(aves)) * intensity
            avg_elast = np.mean([abs(emp_dict[t]["elast"]) for t in selected_tools])

            raw_drop_pct = min(92.0, (combined_ave / 100.0) * avg_elast * 68.0)
            trade_loss_usd = base_trade * (raw_drop_pct / 100.0)
            remaining_usd = base_trade - trade_loss_usd

            if combined_ave >= 55 or ("疫病检疫" in selected_tools and intensity >= 1.2):
                risk_label = "🔴 高风险（极易触发 WTO STC 特别贸易关注或 DSB 专家组磋商）"
            elif combined_ave >= 30:
                risk_label = "🟡 中等风险（可能引发双边技术磋商，需准备充分科学风险评估依据）"
            else:
                risk_label = "🟢 低风险（符合 WTO SPS 协定常规监管范畴，合规抗辩空间大）"

            m1, m2, m3 = st.columns(3)
            m1.metric("综合等效关税率 (AVE)", f"{combined_ave:.1f}%")
            m2.metric("预期双边进口降幅", f"-{raw_drop_pct:.1f}%", f"-{trade_loss_usd:.2f} 亿美元")
            m3.metric("反制后预期进口额", f"{remaining_usd:.2f} 亿美元")

            st.info(f"**WTO 合规与争端触发风险研判**：{risk_label}")

            st.markdown("#### 3. 进口缺口第三方供应链转移分配测算（预计分流 85% 缺口）")
            diversion_total = trade_loss_usd * 0.85
            shares = {"巴西 (BRA)": 0.42, "阿根廷 (ARG)": 0.22, "乌拉圭 (URY)": 0.16, "新西兰 (NZL)": 0.12, "其他供应国": 0.08}
            df_div = pd.DataFrame([
                {"替代供应方": k, "承接转移份额": f"{v*100:.0f}%", "预计新增对华出口额 (亿美元)": round(diversion_total * v, 2)}
                for k, v in shares.items() if k != target_country
            ])
            st.dataframe(df_div, width="stretch", hide_index=True)
