import streamlit as st
import sqlite3

st.set_page_config(page_title="كاشير الكشك Pro", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>.block-container {padding: 0.5rem 1rem;} .stButton button {padding: 4px 8px;}</style>", unsafe_allow_html=True)

# تفعيل قاعدة بيانات v35 نظيفة بالكامل تعمل تلقائياً بالمكتبات الافتراضية المدمجة
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
cat_dict = {row[1]: row[0] for row in cats_raw}
cat_names = list(cat_dict.keys())

with t1:
    cl, cr = st.columns(2)
    with cr:
        active_cart = st.selectbox("الزبون:", list(st.session_state.carts.keys()))
        f_cat = st.radio("📂 تصفية المنتجات حسب العائلة:", ["الكل"] + cat_names, horizontal=True)
        
        if f_cat == "الكل": cursor.execute("SELECT * FROM products")
        else: cursor.execute("SELECT * FROM products WHERE category_id=?", (cat_dict[f_cat],))
        prods = cursor.fetchall()
        
        if prods:
            p_cols = st.columns(3)
            for idx, p in enumerate(prods):
                with p_cols[idx % 3]:
                    st.markdown(f"<div style='background:#F8F9FA; padding:5px; border-radius:6px; text-align:center; border:1px solid #DEE2E6;'>📦 <b>{p[1]}</b><br><span style='color:#1E88E5; font-size:11px;'>علبة: {p[5]}دج | قارو: {p[6]}دج</span></div>", unsafe_allow_html=True)
                    b_type = st.selectbox("النوع:", ["بالعلبة", "بالقارو"], key=f"t_{idx}_{p[0]}")
                    b_qty = st.number_input("الكمية المطلوبة يدوياً:", min_value=1.0, value=1.0, step=1.0, key=f"q_{idx}_{p[0]}")
                    
                    if st.button(f"➕ إضافة {p[1][:8]}", key=f"b_{idx}_{p[0]}"):
                        fp = p[5] if "علبة" in b_type else p[6]
                        sd = b_qty if "علبة" in b_type else b_qty / p[7]
                        prof = (p[5]-p[4]) * b_qty if "علبة" in b_type else (p[6]-(p[4]/p[7])) * b_qty
                        
                        existing_item = None
                        for item in st.session_state.carts[active_cart]:
                            if item['barcode'] == p[0] and item['type'] == b_type:
                                existing_item = item
                                break
                        if existing_item:
                            existing_item['qty'] += b_qty
                            existing_item['total'] += fp * b_qty
                            existing_item['profit'] += prof
                            existing_item['deduction'] += sd
                        else:
                            st.session_state.carts[active_cart].append({'barcode': p[0], 'name': p[1], 'type': b_type, 'qty': b_qty, 'price': fp, 'total': fp * b_qty, 'profit': prof, 'deduction': sd})
                        st.rerun()
                        
        b_scan = st.text_input("🔍 أو امسح باركود للبيع السريع:")
        if b_scan:
            cursor.execute("SELECT * FROM products WHERE barcode=?", (b_scan,))
            r = cursor.fetchone()
            if r and st.button(f"🛒 تأكيد إضافة السلعة: {r[1]}"):
                st.session_state.carts[active_cart].append({'barcode': r[0], 'name': r[1], 'type': "بالعلبة", 'qty': 1.0, 'price': r[5], 'total': r[5], 'profit': (r[5]-r[4]), 'deduction': 1.0})
                st.rerun()
    with cl:
        st.markdown("##### 🛒 سلة المبيعات")
        if st.session_state.carts[active_cart]:
            # استخدام مصفوفة عادية لعرض السلة دون الحاجة لمكتبة بانداز الثقيلة
            cart_data = st.session_state.carts[active_cart]
            st.table([{"الاسم": i['name'], "النوع": i['type'], "الكمية": i['qty'], "المجموع": i['total']} for i in cart_data])
            tot = sum(i['total'] for i in cart_data)
            st.markdown(f"#### 💰 الحساب الإجمالي: {tot:,} دج")
            pay = st.radio("طريقة الدفع:", ["كاش", "كريدي"], horizontal=True)
            c_name = st.text_input("اسم الزبون المدين:") if "كريدي" in pay else ""
            if st.button("🚀 تأكيد وحفظ البيع", type="primary", use_container_width=True):
                if "كريدي" in pay and c_name: cursor.execute("INSERT INTO debts (customer_name, total_amount, remaining) VALUES (?, ?, ?)", (c_name, tot, tot))
                for i in cart_data:
                    cursor.execute("INSERT INTO sales (barcode, name, sale_type, qty, total_price, profit) VALUES (?, ?, ?, ?, ?, ?)", (i['barcode'], i['name'], i['type'], i['qty'], i['total'], i['profit']))
                    cursor.execute("UPDATE products SET stock_box = stock_box - ? WHERE barcode = ?", (i['deduction'], i['barcode']))
                conn.commit()
                st.session_state.carts[active_cart] = []
                st.success("✅ تم الحفظ بنجاح!")
                st.rerun()
        else: st.info("السلة فارغة حالياً.")

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
                except: st.error("⚠️ مسجلة سابقاً.")

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
            p_p = st.number_input("سعر بيع القارو تجزئة (دج):")
            stk = st.number_input("المخزون بالعلب:")
        if st.form_submit_button("💾 حفظ السلعة وتفعيل زر اللمس", use_container_width=True):
            if bc and nm:
                cursor.execute("INSERT OR REPLACE INTO products (barcode, name, category_id, unit_type, buy_price_box, sell_box, sell_piece, pieces_per_box, stock_box, min_stock) VALUES (?, ?, ?, 'قطعة', ?, ?, ?, ?, ?, 5.0)", (bc, nm, cat_dict[cc], c_p, b_p, p_p, int(p_box), stk))
                conn.commit()
                st.success("✅ تم بنجاح جرد السلعة!")
                st.rerun()
    cursor.execute("SELECT barcode, name, sell_box, stock_box FROM products")
    st.table([{"الباركود": r[0], "الاسم": r[1], "بيع العلبة": r[2], "المخزون": r[3]} for r in cursor.fetchall()])

with t2:
    st.subheader("⚡ تعبئة سلع الموردين")
    s_bc = st.text_input("امسح باركود السلعة للتعبئة:")
    if s_bc:
        cursor.execute("SELECT * FROM products WHERE barcode=?", (s_bc,))
        pr = cursor.fetchone()
        if pr:
            with st.form("r_form"):
                aq = st.number_input("الكمية المضافة للمخزن:", value=10.0)
                nb = st.number_input("سعر الشراء الجديد:", value=pr[4])
                ns = st.number_input("سعر بيع العلبة الجديد:", value=pr[5])
                np = st.number_input("سعر بيع القطعة الجديد:", value=pr[6])
                if st.form_submit_button("💾 تحديث فوري"):
                    cursor.execute("UPDATE products SET stock_box = stock_box + ?, buy_price_box=?, sell_box=?, sell_piece=? WHERE barcode=?", (aq, nb, ns, np, s_bc))
                    conn.commit()
                    st.success("✅ تم التحديث!")

with t4:
    st.subheader("📋 كارني ديون الكشك (الكريدي)")
    cursor.execute("SELECT id, customer_name, total_amount, remaining FROM debts WHERE remaining > 0")
    st.table([{"رقم الحساب": r[0], "اسم الزبون": r[1], "الدين الكلي": r[2], "المبلغ المتبقي": r[3]} for r in cursor.fetchall()])

with t5:
    st.subheader("📊 أرباح الصندوق الصافية")
    cursor.execute("SELECT id, name, total_price, profit, date FROM sales")
    sales_list = cursor.fetchall()
    if sales_list:
        st.markdown(f"### 💰 مجموع الأرباح الصافية الحالية بالخزينة: {sum(r[3] for r in sales_list):,.2f} دج")
    st.table([{"رقم العملية": r[0], "السلعة": r[1], "المدخول": r[2], "الربح الصافي": r[3], "الوقت": r[4]} for r in sales_list])
