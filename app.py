import streamlit as st
import pandas as pd
import sqlite3
import datetime

# إعدادات الواجهة البصرية المتكاملة للمتصفح والتابلت
st.set_page_config(page_title="نظام كاشير الكشك الذكي المطور", layout="wide", initial_sidebar_state="expanded")

# الاتصال بقاعدة البيانات السحابية
conn = sqlite3.connect("kiosk_cloud_db.db", check_same_thread=False)
cursor = conn.cursor()

# تأسيس الجداول
cursor.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
cursor.execute("CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, company TEXT)")
cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                  (barcode TEXT PRIMARY KEY, name TEXT, category_id INTEGER, unit_type TEXT, 
                   buy_price_box REAL, sell_box REAL, sell_piece REAL, pieces_per_box INTEGER, stock_box REAL, min_stock REAL, supplier_id INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS sales 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT, name TEXT, category_name TEXT,
                   sale_type TEXT, qty REAL, total_price REAL, profit REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS debts 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, total_amount REAL, remaining REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS receipts_archive 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, items_html TEXT, total_amount REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

# نظام السلال لـ 5 زبائن متزامنين
if 'carts' not in st.session_state:
    st.session_state.carts = {f"🛒 الزبون رقم {i}": [] for i in range(1, 6)}

st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🏪 نظام كاشير وتسيير مبيعات الكشك الذكي Pro</h1>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🛒 كاشير المبيعات السريعة", 
    "⚡ التموين وتحديث الأسعار", 
    "📦 المخزن وجرد السلع", 
    "💵 سجل الديون (الكارني)", 
    "📊 الأرباح وحساب الفائدة",
    "🗂️ تهيئة العائلات والموردين"
])

# ----------------- 1. كاشير المبيعات السريعة -----------------
with tab1:
    st.subheader("⚡ نقطة البيع السريع لعدة زبائن معاً")
    active_cart = st.selectbox("📌 اختر الزبون الحالي:", list(st.session_state.carts.keys()))
    barcode_scan = st.text_input("امسح باركود السلعة بالقارئ للبيع:", key=f"scan_{active_cart}")
    
    if barcode_scan:
        cursor.execute("SELECT * FROM products WHERE barcode=?", (barcode_scan,))
        prod = cursor.fetchone()
        if prod:
            st.success(f"📦 السلعة: **{prod[1]}** | المتوفر: {prod[8]:.2f} علبة")
            s_type = st.radio("نوع البيع:", ["بالعلبة كاملة/الجملة", "بالقارو / بالقطعة منفردة"] if prod[7] > 1 else ["بالقطعة (وحدة)", "بالوزن (كيلوغرام)"])
            qty = st.number_input("الكمية المطلوبة:", min_value=0.01, value=1.0)
            
            if s_type == "بالعلبة كاملة/الجملة" or s_type == "بالقطعة (وحدة)":
                price = prod[5]
                stock_deduction = qty
                profit = (prod[5] - prod[4]) * qty
            elif s_type == "بالقارو / بالقطعة منفردة":
                price = prod[6]
                stock_deduction = qty / prod[7]
                profit = (prod[6] - (prod[4]/prod[7])) * qty
            else:
                price = prod[5]
                stock_deduction = qty
                profit = (prod[5] - prod[4]) * qty
                
            if st.button("➕ إضافة إلى السلة"):
                st.session_state.carts[active_cart].append({
                    'barcode': barcode_scan, 'name': prod[1], 'type': s_type, 'qty': qty, 'price': price, 'total': qty * price, 'profit': profit, 'deduction': stock_deduction
                })
                st.rerun()
        else:
            st.error("❌ المنتج غير مسجل.")

    if st.session_state.carts[active_cart]:
        df_cart = pd.DataFrame(st.session_state.carts[active_cart])
        st.dataframe(df_cart[['name', 'type', 'qty', 'price', 'total']], use_container_width=True)
        cart_total = df_cart['total'].sum()
        st.markdown(f"### 💰 الإجمالي: {cart_total:,} دج")
        
        pay_method = st.selectbox("طريقة الدفع:", ["نقداً", "كريدي"])
        customer_name = st.text_input("اسم الزبون:") if pay_method == "كريدي" else ""
        
        if st.button("🚀 تأكيد البيع وحفظ الفاتورة"):
            if pay_method == "كريدي" and customer_name:
                cursor.execute("INSERT INTO debts (customer_name, total_amount, remaining) VALUES (?, ?, ?)", (customer_name, cart_total, cart_total))
            for item in st.session_state.carts[active_cart]:
                cursor.execute("INSERT INTO sales (barcode, name, sale_type, qty, total_price, profit) VALUES (?, ?, ?, ?, ?, ?)",
                               (item['barcode'], item['name'], item['type'], item['qty'], item['total'], item['profit']))
                cursor.execute("UPDATE products SET stock_box = stock_box - ? WHERE barcode = ?", (item['deduction'], item['barcode']))
            conn.commit()
            st.session_state.carts[active_cart] = []
            st.success("✅ تم البيع بنجاح!")
            st.rerun()

# ----------------- 2. واجهة التموين -----------------
with tab2:
    st.subheader("⚡ استقبال وتعبئة سلع الموردين")
    supply_barcode = st.text_input("امسح باركود السلعة المستلمة:")
    if supply_barcode:
        cursor.execute("SELECT * FROM products WHERE barcode=?", (supply_barcode,))
        prod_refill = cursor.fetchone()
        if prod_refill:
            st.info(f"📥 السلعة: **{prod_refill[1]}**")
            with st.form("refill_form"):
                added_qty = st.number_input("الكمية المضافة جديدة:", value=10.0)
                new_buy = st.number_input("سعر الشراء الجديد للعلبة:", value=prod_refill[4])
                new_box_sell = st.number_input("سعر بيع العلبة الجديد:", value=prod_refill[5])
                new_piece_sell = st.number_input("سعر بيع القطعة الجديد:", value=prod_refill[6])
                if st.form_submit_button("💾 تحديث فوري"):
                    cursor.execute("UPDATE products SET stock_box = stock_box + ?, buy_price_box=?, sell_box=?, sell_piece=? WHERE barcode=?", 
                                   (added_qty, new_buy, new_box_sell, new_piece_sell, supply_barcode))
                    conn.commit()
                    st.success("✅ تم التحديث!")

# ----------------- 3. المخزن وجرد السلع (مصحح بالكامل) -----------------
with tab3:
    st.subheader("📥 تسجيل السلع الجديدة لأول مرة")
    with st.form("add_new_product_form"):
        b_code = st.text_input("باركود السلعة الجديدة:")
        p_name = st.text_input("اسم السلعة بالتفصيل:")
        u_type = st.selectbox("طريقة القياس والبيع الأساسية:", ["بالقطعة (وحدة/علبة)", "بالوزن (كيلوغرام)"])
        pieces_in_box = st.number_input("عدد القطع/القارو داخل العلبة الواحدة (20 للسجائر):", min_value=1, value=1)
        cost_p = st.number_input("سعر شراء العلبة الكاملة من المورد (دج):", min_value=0.0, value=0.0)
        box_p = st.number_input("سعر بيع العلبة كاملة للمستهلك (دج):", min_value=0.0, value=0.0)
        piece_p = st.number_input("سعر بيع القارو الواحد / القطعة منفردة (دج):", min_value=0.0, value=0.0)
        curr_stock = st.number_input("إجمالي المخزون الابتدائي المتوفر حالياً (علب):", min_value=0.0, value=0.0)
        min_stock = st.number_input("حد التنبيه عند قرب النفاد:", min_value=1.0, value=5.0)
            
        if st.form_submit_button("💾 حفظ السلعة الجديدة بنجاح", use_container_width=True):
            if b_code and p_name:
                cursor.execute("INSERT OR REPLACE INTO products (barcode, name, category_id, unit_type, buy_price_box, sell_box, sell_piece, pieces_per_box, stock_box, min_stock, supplier_id) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, 1)",
                               (b_code, p_name, u_type, cost_p, box_p, piece_p, int(pieces_in_box), curr_stock, min_stock))
                conn.commit()
                st.success(f"تم بنجاح حفظ المنتج **'{p_name}'**!")
                st.rerun()

    st.markdown("#### 📋 قائمة المخزن")
    df_products = pd.read_sql_query("SELECT barcode, name, sell_box, sell_piece, stock_box FROM products", conn)
    st.dataframe(df_products, use_container_width=True)

# ----------------- 4. سجل الديون -----------------
with tab4:
    st.subheader("📋 كارني ديون الكشك الرقمي")
    df_debts = pd.read_sql_query("SELECT id, customer_name, total_amount, remaining FROM debts WHERE remaining > 0", conn)
    st.dataframe(df_debts, use_container_width=True)

# ----------------- 5. الأرباح وحساب الفائدة -----------------
with tab5:
    st.subheader("📊 جرد حساب الفائدة وأرباح الصندوق")
    df_sales_raw = pd.read_sql_query("SELECT * FROM sales", conn)
    if not df_sales_raw.empty:
        st.metric("💰 مجموع الأرباح الصافية الحالية", f"{df_sales_raw['profit'].sum():,.2f} دج")
        st.dataframe(df_sales_raw, use_container_width=True)

# ----------------- 6. العائلات -----------------
with tab6:
    st.subheader("🗂️ تصنيف الموردين والعائلات")
    st.info("النظام جاهز ومفعل تلقائياً.")
