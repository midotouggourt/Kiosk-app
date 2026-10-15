import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
from PIL import Image

st.set_page_config(page_title="كاشير الكشك Pro", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>.block-container {padding: 0.5rem 1rem;} .stButton button {padding: 4px 8px;}</style>", unsafe_allow_html=True)

# تفعيل قاعدة بيانات v16 مع ترتيب الحقول الدقيق لمنع خطأ الحفظ
conn = sqlite3.connect("kiosk_cloud_final_v16.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                  (barcode TEXT PRIMARY KEY, name TEXT, category_id INTEGER, unit_type TEXT, 
                   buy_price_box REAL, sell_box REAL, sell_piece REAL, pieces_per_box INTEGER, stock_box REAL, min_stock REAL, image_blob BLOB)''')
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
cat_dict = {row: row for row in cats_raw}
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
                with p_cols[idx % 3]:
                    st.markdown(f"<div style='background:#F8F9FA; padding:5px; border-radius:6px; text-align:center; border:1px solid #DEE2E6;'><b>{p}</b><br><span style='color:#1E88E5; font-size:11px;'>علبة: {p}دج | قارو: {p}دج</span></div>", unsafe_allow_html=True)
                    
                    b_type = st.selectbox("النوع:", ["بالعلبة", "بالقارو"], key=f"t_{idx}_{p}")
                    b_qty = st.number_input("الكمية المطلوبة يدوياً:", min_value=1.0, value=1.0, step=1.0, key=f"q_{idx}_{p}")
                    
                    if st.button(f"➕ إضافة {p[:8]}", key=f"b_{idx}_{p}"):
                        fp = p if "علبة" in b_type else p
                        sd = b_qty if "علبة" in b_type else b_qty / p
                        prof = (p-p) * b_qty if "علبة" in b_type else (p-(p/p)) * b_qty
                        
                        existing_item = None
                        for item in st.session_state.carts[active_cart]:
                            if item['barcode'] == p and item['type'] == b_type:
                                existing_item = item
                                break
                        
                        if existing_item:
                            existing_item['qty'] += b_qty
                            existing_item['total'] += fp * b_qty
                            existing_item['profit'] += prof
                            existing_item['deduction'] += sd
                        else:
                            st.session_state.carts[active_cart].append({
                                'barcode': p, 'name': p, 'type': b_type, 'qty': b_qty, 'price': fp, 'total': fp * b_qty, 'profit': prof, 'deduction': sd
                            })
                        st.rerun()
                        
        b_scan = st.text_input("🔍 أو امسح باركود / اكتب اسم السلعة يدوياً هنا للبحث:")
        if b_scan:
            cursor.execute("SELECT * FROM products WHERE barcode=? OR name LIKE ?", (b_scan, f"%{b_scan}%"))
            r = cursor.fetchone()
            if r and st.button(f"🛒 تأكيد إضافة السلعة المبحوث عنها: {r}"):
                st.session_state.carts[active_cart].append({'barcode': r, 'name': r, 'type': "بالعلبة", 'qty': 1.0, 'price': r, 'total': r, 'profit': (r-r), 'deduction': 1.0})
                st.rerun()
    with cl:
        st.markdown("##### 🛒 سلة المبيعات للحساب الحالي")
        if st.session_state.carts[active_cart]:
            df = pd.DataFrame(st.session_state.carts[active_cart])
            display_cols = [c for c in ['name', 'type', 'qty', 'total'] if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True, height=140)
            tot = df['total'].sum()
            st.markdown(f"#### 💰 الحساب الإجمالي: {tot:,} دج")
            pay = st.radio("طريقة الدفع للمركز:", ["كاش", "كريدي"], horizontal=True)
            c_name = st.text_input("اسم الزبون المدين (للكارني):") if "كريدي" in pay else ""
            if st.button("🚀 تأكيد وحفظ البيع", type="primary", use_container_width=True):
                if "كريدي" in pay and c_name: cursor.execute("INSERT INTO debts (customer_name, total_amount, remaining) VALUES (?, ?, ?)", (c_name, tot, tot))
                for i in st.session_state.carts[active_cart]:
                    cursor.execute("INSERT INTO sales (barcode, name, sale_type, qty, total_price, profit) VALUES (?, ?, ?, ?, ?, ?)", (i['barcode'], i['name'], i['type'], i['qty'], i['total'], i['profit']))
                    cursor.execute("UPDATE products SET stock_box = stock_box - ? WHERE barcode = ?", (i['deduction'], i['barcode']))
                conn.commit()
                st.session_state.carts[active_cart] = []
                st.success("✅ تم الحفظ وتصفير السلة بنجاح!")
                st.rerun()
        else:
            st.info("السلة فارغة حالياً. اضغط على أزرار المنتجات الملوّنة في اليمين للبيع السريع.")

with t3:
    st.markdown("#### 📂 1. إدارة وتهيئة عائلات المنتجات")
    with st.form("cat_form"):
        new_cat_input = st.text_input("اكتب اسم عائلة جديدة لتظهر كـ زر لمس (مثال: عائلة السجائر، مشروبات غازية):")
        if st.form_submit_button("💾 حفظ وتفعيل العائلة الجديدة فوراً"):
            if new_cat_input:
                try:
                    cursor.execute("INSERT INTO categories (name) VALUES (?)", (new_cat_input.strip(),))
                    conn.commit()
                    st.success(f"✅ تم تفعيل عائلة '{new_cat_input}' بنجاح في نظام الأزرار!")
                    st.rerun()
                except: st.error("⚠️ هذه العائلة مسجلة سابقاً في كشكك.")

    st.markdown("---")
    st.markdown("#### 📦 2. تسجيل السلع وتعبئة الرفوف")
    with st.form("p_form"):
        i1, i2 = st.columns(2)
        with i1:
            bc = st.text_input("باركود السلعة الجديدة (امسح بالقارئ):")
            nm = st.text_input("اسم السلعة بالتفصيل (روثمانز، كوكا...):")
            cc = st.selectbox("حدد العائلة التي تتبع لها هذه السلعة:", cat_names)
            p_box = st.number_input("عدد السجائر/القطع في العلة الواحدة (اكتب 20 للسجائر):", min_value=1, value=20)
        with i2:
            c_p = st.number_input("سعر شراء العلبة من المورد (دج):")
            b_p = st.number_input("سعر بيع العلبة كاملة (دج):")
            p_p = st.number_input("سعر بيع القارو الواحد تجزئة (دج):")
            stk = st.number_input("المخزون المتوفر حالياً بالعلب:")
        if st.form_submit_button("💾 حفظ السلعة وتفعيل زر اللمس في الكاشير", use_container_width=True):
            if bc and nm:
                # تصحيح دقيق لعدد المتغيرات ومكان الـ NULL لتطابق 11 عمود بروتوكولي في الجدول
                cursor.execute("INSERT OR REPLACE INTO products (barcode, name, category_id, unit_type, buy_price_box, sell_box, sell_piece, pieces_per_box, stock_box, min_stock, image_blob) VALUES (?, ?, ?, 'قطعة', ?, ?, ?, ?, ?, 5.0, NULL)", (bc, nm, cat_dict[cc], cost_p, box_p, piece_p, int(p_box), stk))
                conn.commit()
                st.success(f"✅ تم بنجاح جرد السلعة وتثبيتها تحت عائلة '{cc}'!")
                st.rerun()
    st.dataframe(pd.read_sql_query("SELECT barcode as 'الباركود', name as 'الاسم', sell_box as 'بيع العلبة', stock_box as 'المخزون' FROM products", conn), use_container_width=True)

with t2:
    st.subheader("⚡ تعبئة سلع الموردين")
    s_bc = st.text_input("امسح باركود السلعة للتعبئة السريعة:")
    if s_bc:
        cursor.execute("SELECT * FROM products WHERE barcode=?", (s_bc,))
        pr = cursor.fetchone()
        if pr:
            with st.form("r_form"):
                aq = st.number_input("الكمية المضافة للمخزن:", value=10.0)
                nb = st.number_input("سعر الشراء الجديد:", value=pr)
                ns = st.number_input("سعر بيع العلبة الجديد:", value=pr)
                np = st.number_input("سعر بيع القطعة الجديد:", value=pr)
                if st.form_submit_button("💾 تحديث فوري"):
                    cursor.execute("UPDATE products SET stock_box = stock_box + ?, buy_price_box=?, sell_box=?, sell_piece=? WHERE barcode=?", (aq, nb, ns, np, s_bc))
                    conn.commit()
                    st.success("✅ تم التحديث وفهرسة الأسعار الجديدة!")

with t4:
    st.subheader("📋 كارني ديون الكشك (الكريدي)")
    st.dataframe(pd.read_sql_query("SELECT id as 'رقم الحساب', customer_name as 'اسم الزبون', total_amount as 'الدين الكلي', remaining as 'المبلغ المتبقي عليه' FROM debts WHERE remaining > 0", conn), use_container_width=True)

with t5:
