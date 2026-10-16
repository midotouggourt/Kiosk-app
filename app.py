import streamlit as st
import sqlite3

st.set_page_config(page_title="كاشير الكشك Pro", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>.block-container {padding: 0.5rem 1rem;} .stButton button {padding: 4px 8px;}</style>", unsafe_allow_html=True)

conn = sqlite3.connect("kiosk_cloud_final_v35.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                  (barcode TEXT PRIMARY KEY, name TEXT, category_id INTEGER, unit_type TEXT, 
                   buy_price_box REAL, sell_box REAL, sell_piece REAL, pieces_per_box INTEGER, stock_box REAL, min_stock REAL)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT, name TEXT, sale_type TEXT, qty REAL, total_price REAL, profit REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS debts (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, total_amount REAL, remaining REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

cursor.execute("INSERT OR IGNORE INTO categories (id, name) VALUES (1, 'عام / كشك')")
conn.commit()

if 'carts' not in st.session_state:
    st.session_state.carts = {f"🛒 زبون {i}": [] for i in range(1, 4)}

st.markdown("<h3 style='text-align: center; color: #1E88E5; margin:0;'>🏪 كاشير الكشك الرقمي المتكامل</h3>", unsafe_allow_html=True)
t1, t2, t3, t4, t5 = st.tabs(["🛒 كاشير المبيعات", "⚡ التموين والأسعار", "📦 المخزن والسلع", "💵 سجل الكريدي", "📊 الأرباح"])

cursor.execute("SELECT id, name FROM categories")
cats_raw = cursor.fetchall()
# تحويل العائلات إلى قاموس يسهل التعامل معه بدقة
cat_dict = {row[1]: row[0] for row in cats_raw}
cat_names = list(cat_dict.keys())

with t1:
    cl, cr = st.columns(2)
    with cr:
        active_cart = st.selectbox("الزبون:", list(st.session_state.carts.keys()))
        f_cat = st.radio("📂 تصفية المنتجات حسب العائلة:", ["الكل"] + cat_names, horizontal=True)
        
        if f_cat == "الكل": 
            cursor.execute("SELECT * FROM products")
        else: 
            cursor.execute("SELECT * FROM products WHERE category_id=?", (cat_dict[f_cat],))
        prods = cursor.fetchall()
        
        if prods:
            p_cols = st.columns(3)
            for idx, p in enumerate(prods):
                p_barcode, p_name, p_cat_id, p_unit, p_buy_box, p_sell_box, p_sell_piece, p_pieces_per_box, p_stock, p_min = p
                with p_cols[idx % 3]:
                    st.markdown(f"<div style='background:#F8F9FA; padding:5px; border-radius:6px; text-align:center; border:1px solid #DEE2E6;'>📦 <b>{p_name}</b><br><span style='color:#1E88E5; font-size:11px;'>علبة: {p_sell_box}دج | قارو: {p_sell_piece}دج</span></div>", unsafe_allow_html=True)
                    b_type = st.selectbox("النوع:", ["بالعلبة", "بالقارو"], key=f"t_{idx}_{p_barcode}")
                    b_qty = st.number_input("الكمية المطلوبة يدوياً:", min_value=1.0, value=1.0, step=1.0, key=f"q_{idx}_{p_barcode}")
                    
                    if st.button(f"➕ إضافة {p_name[:8]}", key=f"b_{idx}_{p_barcode}"):
                        fp = p_sell_box if "علبة" in b_type else p_sell_piece
                        sd = b_qty if "علبة" in b_type else b_qty / p_pieces_per_box
                        
                        # حساب الأرباح الصافية بدقة بناءً على التجزئة أو العلبة كاملة
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
                        
        b_scan = st.text_input("🔍 أو امسح باركود للبيع السريع:")
        if b_scan:
            cursor.execute("SELECT * FROM products WHERE barcode=?", (b_scan,))
            r = cursor.fetchone()
            if r:
                r_barcode, r_name, r_cat_id, r_unit, r_buy_box, r_sell_box, r_sell_piece, r_pieces_per_box, r_stock, r_min = r
                st.session_state.carts[active_cart].append({
                    'barcode': r_barcode, 'name': r_name, 'type': "بالعلبة", 'qty': 1.0, 'price': r_sell_box, 
                    'total': r_sell_box, 'profit': (r_sell_box - r_buy_box), 'deduction': 1.0, 'unit_profit': (r_sell_box - r_buy_box), 'unit_deduction': 1.0
                })
                st.rerun()
    with cl:
        st.markdown("##### 🛒 سلة المبيعات")
        cart_data = st.session_state.carts[active_cart]
        if cart_data:
            for c_idx, item in enumerate(cart_data):
                st.markdown(f"<div style='padding:5px; border-bottom:1px solid #EEE;'><b>{item['name']}</b> ({item['type']})</div>", unsafe_allow_html=True)
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
                    st.markdown(f"<p style='text-align:center; margin-top:5px;'>الكمية: <b>{int(item['qty'])}</b> | {item['total']}دج</p>", unsafe_allow_html=True)
                with col_q3:
                    if st.button("➕", key=f"pls_{c_idx}_{item['barcode']}_{item['type']}"):
                        item['qty'] += 1
                        item['total'] += item['price']
                        item['profit'] += item['unit_profit']
                        item['deduction'] += item['unit_deduction']
                        st.rerun()
                with col_del:
                    if st.button("❌ حذف السطر", key=f"del_{c_idx}_{item['barcode']}_{item['type']}"):
                        cart_data.pop(c_idx)
                        st.rerun()
            
            tot = sum(i['total'] for i in cart_data)
            st.markdown(f"#### 💰 الحساب الإجمالي: {tot:,} دج")
            pay = st.radio("طريقة الدفع:", ["كاش", "كريدي"], horizontal=True)
            c_name = st.text_input("اسم الزبون المدين:") if "كريدي" in pay else ""
            if st.button("🚀 تأكيد وحفظ البيع", type="primary", use_container_width=True):
                if "كريدي" in pay and c_name: 
                    cursor.execute("INSERT INTO debts (customer_name, total_amount, remaining) VALUES (?, ?, ?)", (c_name, tot, tot))
                for i in cart_data:
                    cursor.execute("INSERT INTO sales (barcode, name, sale_type, qty, total_price, profit) VALUES (?, ?, ?, ?, ?, ?)", (i['barcode'], i['name'], i['type'], i['qty'], i['total'], i['profit']))
                    cursor.execute("UPDATE products SET stock_box = stock_box - ? WHERE barcode = ?", (i['deduction'], i['barcode']))
                conn.commit()
                st.session_state.carts[active_cart] = []
                st.success("✅ تم الحفظ بنجاح!")
                st.rerun()
        else: 
            st.info("السلة فارغة حالياً.")

with t3:
    st.markdown("#### 📂 1. إدارة عائلات المنتجات")
    with st.form("cat_form"):
        new_cat_input = st.text_input("اكتب اسم عائلة جديدة لتظهر كـ زر لمس:")
        if st.form_submit_button("💾 حفظ وتفعيل العائلة الجديدة"):
            if new_cat_input:
                try:
                    cursor.execute("INSERT INTO categories (name) VALUES (?)", (new_cat_input.strip(),))
                    conn.commit()
                    st.success("✅ تم تفعيل العائلة!")
                    st.rerun()
                except: 
                    st.error("⚠️ مسجلة سابقاً.")

    st.markdown("---")
    st.markdown("#### 📦 2. تسجيل السلع وتعبئة الرفوف")
    with st.form("p_form"):
        i1, i2 = st.columns(2)
        with i1:
            bc = st.text_input("باركود السلعة الجديدة (امسح بالقارئ):")
            nm = st.text_input("اسم السلعة بالتفصيل:")
            cc = st.selectbox("حدد العائلة:", cat_names)
            p_box = st.number_input("عدد السجائر/القطع في العلبة:", min_value=1, value=20)
        with i2:
            c_p = st.number_input("سعر الشراء من المورد (دج):")
            b_p = st.number_input("سعر بيع العلبة كاملة (دج):")
