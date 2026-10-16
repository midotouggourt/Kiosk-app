import streamlit as st
import sqlite3
import pandas as pd
import datetime

# 1. إعداد الصفحة لتناسب شاشة التابلت بالكامل بدون تمرير (Scrolling)
st.set_page_config(page_title="كاشير الكشك Pro", layout="wide", initial_sidebar_state="collapsed")

# تنسيق مخصص CSS لتقليل الفراغات وجعل الواجهة مدمجة ومريحة للمس
st.markdown("""
<style>
    .block-container {padding: 0.3rem 0.8rem;}
    .stButton button {padding: 2px 6px; font-size: 14px; width: 100%;}
    .stTabs [data-baseweb="tab-list"] {gap: 4px;}
    .stTabs [data-baseweb="tab"] {padding: 6px 12px; font-size: 14px;}
    div[data-testid="stExpander"] {margin-bottom: 4px;}
</style>
""", unsafe_allow_html=True)

# 2. الاتصال بقاعدة البيانات وإنشاء الجداول المحدثة
conn = sqlite3.connect("kiosk_cloud_final_v36.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                  (barcode TEXT PRIMARY KEY, name TEXT, category_id INTEGER, unit_type TEXT, 
                   buy_price_box REAL, sell_box REAL, sell_piece REAL, pieces_per_box INTEGER, 
                   stock_box REAL, min_stock REAL, image_base64 TEXT, supplier_name TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS sales 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT, name TEXT, sale_type TEXT, 
                   qty REAL, total_price REAL, profit REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS debts 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, total_amount REAL, 
                   remaining REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS suppliers 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, phone TEXT, balance REAL DEFAULT 0.0)''')

# إدراج عائلة افتراضية
cursor.execute("INSERT OR IGNORE INTO categories (id, name) VALUES (1, 'عام / كشك')")
conn.commit()

# 3. إدارة جلسة العمل وسلال الزبائن المتعددة ومخزن الفواتير
if 'carts' not in st.session_state:
    st.session_state.carts = {f"🛒 زبون {i}": [] for i in range(1, 4)}
if 'last_receipt' not in st.session_state:
    st.session_state.last_receipt = None

st.markdown("<h3 style='text-align: center; color: #1E88E5; margin:0; padding:0;'>🏪 كاشير الكشك الرقمي المتكامل</h3>", unsafe_allow_html=True)
t1, t2, t3, t4, t5, t6 = st.tabs(["🛒 كاشير المبيعات", "⚡ التموين والأسعار", "📦 المخزن والسلع", "💵 سجل الكريدي", "🤝 الموردين", "📊 الأرباح والذكاء الاصطناعي"])

cursor.execute("SELECT id, name FROM categories")
cats_raw = cursor.fetchall()
cat_dict = {row[1]: row[0] for row in cats_raw}
cat_names = list(cat_dict.keys())

# --- التبويب الأول: كاشير المبيعات السريع ---
with t1:
    cl, cr = st.columns([5, 7])
    
    with cr:
        active_cart = st.selectbox("الزبون النشط:", list(st.session_state.carts.keys()), label_visibility="collapsed")
        f_cat = st.radio("📂 العائلات:", ["الكل"] + cat_names, horizontal=True)
        
        if f_cat == "الكل": 
            cursor.execute("SELECT * FROM products")
        else: 
            cursor.execute("SELECT * FROM products WHERE category_id=?", (cat_dict[f_cat],))
        prods = cursor.fetchall()
        
        if prods:
            p_cols = st.columns(3)
            for idx, p in enumerate(prods):
                p_barcode, p_name, p_cat_id, p_unit, p_buy_box, p_sell_box, p_sell_piece, p_pieces_per_box, p_stock, p_min, p_img, p_supp = p
                with p_cols[idx % 3]:
                    # عرض المنتجات بشكل مدمج يناسب اللمس مع التمييز البصري بالصور إن وجدت
                    img_html = f"<img src='{p_img}' style='width:40px;height:40px;border-radius:4px;float:right;'>" if p_img else "📦"
                    st.markdown(f"<div style='background:#F8F9FA; padding:4px; border-radius:6px; text-align:center; border:1px solid #DEE2E6; min-height:65px;'>{img_html} <b>{p_name}</b><br><span style='color:#1E88E5; font-size:11px;'>علبة: {p_sell_box} | قطعة: {p_sell_piece}</span></div>", unsafe_allow_html=True)
                    
                    b_type = st.selectbox("النوع:", ["بالعلبة", "بالقارو / قطعة"], key=f"t_{idx}_{p_barcode}", label_visibility="collapsed")
                    b_qty = st.number_input("الكمية:", min_value=1.0, value=1.0, step=1.0, key=f"q_{idx}_{p_barcode}", label_visibility="collapsed")
                    
                    if st.button(f"➕ {p_name[:10]}", key=f"b_{idx}_{p_barcode}"):
                        fp = p_sell_box if "علبة" in b_type else p_sell_piece
                        sd = b_qty if "علبة" in b_type else b_qty / p_pieces_per_box
                        
                        if "علبة" in b_type:
                            prof = (p_sell_box - p_buy_box) * b_qty
                            unit_prof = p_sell_box - p_buy_box
                            unit_deduction = 1.0
                        else:
                            buy_single_piece = p_buy_box / p_pieces_per_box
                            prof = (p_sell_piece - buy_single_piece) * b_qty
                            unit_prof = p_sell_piece - buy_single_piece
                            unit_deduction = 1.0 / p_pieces_per_box
                        
                        existing_item = None
                        for item in st.session_state.carts[active_cart]:
                            if item['barcode'] == p_barcode and item['type'] == b_type:
                                existing_item = item
                                break
                        if existing_item:
                            existing_item['qty'] += b_qty
                            existing_item['total'] += fp * b_qty
                            existing_item['profit'] += prof
                            existing_item['deduction'] += sd
                        else:
                            st.session_state.carts[active_cart].append({
                                'barcode': p_barcode, 'name': p_name, 'type': b_type, 'qty': b_qty, 'price': fp, 
                                'total': fp * b_qty, 'profit': prof, 'deduction': sd, 'unit_profit': unit_prof, 'unit_deduction': unit_deduction
                            })
                        st.rerun()
                        
        b_scan = st.text_input("🔍 امسح الباركود للبيع المباشر السريع:")
        if b_scan:
            cursor.execute("SELECT * FROM products WHERE barcode=?", (b_scan,))
            r = cursor.fetchone()
            if r:
                st.session_state.carts[active_cart].append({
                    'barcode': r[0], 'name': r[1], 'type': "بالعلبة", 'qty': 1.0, 'price': r[5], 
                    'total': r[5], 'profit': (r[5] - r[4]), 'deduction': 1.0, 'unit_profit': (r[5] - r[4]), 'unit_deduction': 1.0
                })
                st.rerun()

    with cl:
        st.markdown("##### 🛒 سلة المبيعات الحالية")
        cart_data = st.session_state.carts[active_cart]
        if cart_data:
            for c_idx, item in enumerate(cart_data):
                st.markdown(f"<div style='padding:2px; border-bottom:1px solid #EEE; font-size:13px;'><b>{item['name']}</b> ({item['type']})</div>", unsafe_allow_html=True)
                col_q1, col_q2, col_q3, col_del = st.columns([1, 2, 1, 2])
                with col_q1:
                    if st.button("➖", key=f"min_{c_idx}_{item['barcode']}_{item['type']}"):
                        if item['qty'] > 1:
                            item['qty'] -= 1
                            item['total'] -= item['price']
                            item['profit'] -= item['unit_profit']
                            item['deduction'] -= item['unit_deduction']
                        else:
                            cart_data.pop(c_idx)
                        st.rerun()
                with col_q2:
                    st.markdown(f"<p style='text-align:center; margin:0; font-size:13px;'><b>{int(item['qty'])}</b> | {item['total']}دج</p>", unsafe_allow_html=True)
                with col_q3:
                    if st.button("➕", key=f"pls_{c_idx}_{item['barcode']}_{item['type']}"):
                        item['qty'] += 1
                        item['total'] += item['price']
                        item['profit'] += item['unit_profit']
                        item['deduction'] += item['unit_deduction']
                        st.rerun()
                with col_del:
                    if st.button("❌", key=f"del_{c_idx}_{item['barcode']}_{item['type']}"):
                        cart_data.pop(c_idx)
                        st.rerun()
            
            tot = sum(i['total'] for i in cart_data)
            st.markdown(f"#### 💰 الإجمالي: {tot:,} دج")
            
            pay = st.radio("طريقة الدفع:", ["كاش", "كريدي"], horizontal=True)
            c_name = st.text_input("اسم الزبون (لحالة الكريدي):") if "كريدي" in pay else ""
            
            # ميزة الطباعة الاختيارية لحفظ وتوفير الورق حسب رغبة الزبون
            print_receipt = st.checkbox("📄 طباعة وصل حراري بعد الحفظ", value=True)
            
            if st.button("🚀 تأكيد وحفظ العملية", type="primary", use_container_width=True):
                if "كريدي" in pay and c_name: 
                    cursor.execute("INSERT INTO debts (customer_name, total_amount, remaining) VALUES (?, ?, ?)", (c_name, tot, tot))
                
                receipt_lines = []
                receipt_lines.append("🏪 كشك الكاشير الرقمي Pro 🏪")
                receipt_lines.append(f"التاريخ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
                receipt_lines.append("-" * 30)
                
                for i in cart_data:
