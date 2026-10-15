import streamlit as st
import pandas as pd
import sqlite3
import datetime

# إعدادات الواجهة البصرية المتكاملة
st.set_page_config(page_title="نظام كاشير الكشك الذكي المطور", layout="wide", initial_sidebar_state="expanded")

# الاتصال بقاعدة البيانات السحابية (تنشأ تلقائياً في السيرفر)
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

# نظام السلال لـ 5 زبائن متزامنين في ذاكرة المتصفح
if 'carts' not in st.session_state:
    st.session_state.carts = {f"🛒 الزبون رقم {i}": [] for i in range(1, 6)}

# تصميم العنوان البصري العلوي
st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🏪 نظام كاشير وتسيير مبيعات الكشك الذكي Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #757575;'>واجهة سحابية سريعة مخصصة لشاشات اللمس والتابلت</p>", unsafe_allow_html=True)

# تقسيم التطبيق إلى أقسام ملوّنة تفاعلية
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
    
    # تنبيهات نقص المخزن في واجهة ملوّنة
    cursor.execute("SELECT name, stock_box, min_stock FROM products WHERE stock_box <= min_stock")
    low_stock_items = cursor.fetchall()
    for item in low_stock_items:
        st.error(f"⚠️ **تنبيه مخزون منخفض:** السلعة **[{item[0]}]** أوشكت على النفاد، المتبقي: {item[1]:.2f} علبة/وحدة!")

    col_select, col_barcode = st.columns(2)
    with col_select:
        active_cart = st.selectbox("📌 اختر الزبون الحالي:", list(st.session_state.carts.keys()))
    with col_barcode:
        barcode_scan = st.text_input("امسح باركود السلعة بالقارئ أو اكتبه هنا:", key=f"scan_{active_cart}")
    
    if barcode_scan:
        cursor.execute("SELECT p.*, c.name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE p.barcode=?", (barcode_scan,))
        prod = cursor.fetchone()
        
        if prod:
            st.success(f"📦 تم رصد السلعة: **{prod[1]}** | المخزون المتوفر: **{prod[8]:.2f}** علبة/وحدة")
            
            col_t, col_q = st.columns(2)
            with col_t:
                s_type = st.radio("نوع عملية البيع للزبون:", ["بالعلبة كاملة/الجملة", "بالقارو / بالقطعة منفردة"] if prod[7] > 1 else ["بالقطعة (وحدة)", "بالوزن (كيلوغرام)"], key=f"type_{active_cart}")
            with col_q:
                qty = st.number_input("الكمية أو الوزن المطلوبة:", min_value=0.01 if "الوزن" in s_type else 1.0, value=1.0, step=1.0, key=f"qty_{active_cart}")
            
            if s_type in ["بالعلبة كاملة/الجملة", "بالقطعة (وحدة)"]:
                price = prod[5]
                stock_deduction = qty
                profit = (prod[5] - prod[4]) * qty
            elif s_type == "بالقارو / بالقطعة منفردة":
                price = prod[6]
                stock_deduction = qty / prod[7]
                single_cost = prod[4] / prod[7]
                profit = (prod[6] - single_cost) * qty
            else: # الوزن
                price = prod[5]
                stock_deduction = qty
                profit = (prod[5] - prod[4]) * qty
                
            if st.button(f"➕ إضافة السلعة إلى سلة [{active_cart}]", use_container_width=True):
                st.session_state.carts[active_cart].append({
                    'barcode': prod[0], 'name': prod[1], 'type': s_type, 'qty': qty, 'price': price, 'total': qty * price, 'profit': profit, 'deduction': stock_deduction
                })
                st.rerun()
        else:
            st.error("❌ هذا المنتج غير مسجل في مخزن الكشك مسبقاً! يرجى إضافته من قسم المخزن.")

    # استعراض السلة الحالية للزبون المختار بتصميم تفاعلي
    st.markdown(f"#### 🛒 محتويات سلة مبيعات: **{active_cart}**")
    if st.session_state.carts[active_cart]:
        df_cart = pd.DataFrame(st.session_state.carts[active_cart])
        st.dataframe(df_cart[['name', 'type', 'qty', 'price', 'total']], use_container_width=True)
        
        cart_total = df_cart['total'].sum()
        st.markdown(f"### 💰 المبلغ الإجمالي المطلوب: <span style='color:#2E7D32;'>{cart_total:,} دج</span>", unsafe_allow_html=True)
        
        col_pay, col_cust = st.columns(2)
        with col_pay:
            pay_method = st.selectbox("طريقة الدفع للصندوق:", ["نقداً (قيد الخزينة اليومية)", "دفع مؤجل (تسجيل في الكريدي)"], key=f"pay_{active_cart}")
        with col_cust:
            customer_name = st.text_input("اسم الزبون المدين (في حال الكريدي):", key=f"cust_{active_cart}")
            
        col_act1, col_action2 = st.columns(2)
        with col_act1:
            if st.button("🚀 تأكيد البيع وحفظ الإيصال", type="primary", use_container_width=True):
                if "الكريدي" in pay_method and customer_name:
                    cursor.execute("INSERT INTO debts (customer_name, total_amount, remaining) VALUES (?, ?, ?)", (customer_name, cart_total, cart_total))
                
                rows_html = ""
                for item in st.session_state.carts[active_cart]:
                    cursor.execute("INSERT INTO sales (barcode, name, category_name, sale_type, qty, total_price, profit) VALUES (?, ?, 'كشك', ?, ?, ?, ?)",
                                   (item['barcode'], item['name'], item['type'], item['qty'], item['total'], item['profit']))
                    cursor.execute("UPDATE products SET stock_box = stock_box - ? WHERE barcode = ?", (item['deduction'], item['barcode']))
                    rows_html += f"<tr><td>{item['name']}</td><td>{item['qty']}</td><td>{item['total']:,} دج</td></tr>"
                
                cursor.execute("INSERT INTO receipts_archive (items_html, total_amount) VALUES (?, ?)", (rows_html, cart_total))
                conn.commit()
                st.session_state.carts[active_cart] = []
                st.success("✅ تمت العملية بنجاح وتم حفظ الفاتورة في النظام!")
                st.balloons()
                st.rerun()
        with col_action2:
            if st.button("🗑️ إفراغ وإلغاء هذه السلة بالكامل", use_container_width=True):
                st.session_state.carts[active_cart] = []
                st.rerun()
    else:
        st.info("سلة هذا الزبون فارغة حالياً. امسح السلع لإضافتها.")

# ----------------- 2. واجهة التموين وتحديث الأسعار -----------------
with tab2:
    st.subheader("⚡ استقبال وتعبئة سلع الموردين وتعديل الأسوام")
    supply_barcode = st.text_input("امسح باركود السلعة المستلمة لتحديث مخزونها وسعرها:")
    if supply_barcode:
        cursor.execute("SELECT * FROM products WHERE barcode=?", (supply_barcode,))
        prod_refill = cursor.fetchone()
        if prod_refill:
            st.info(f"📥 السلعة المكتشفة: **{prod_refill[1]}** | المخزون الحالي: **{prod_refill[8]:.2f}** علبة/وحدة")
            with st.form("quick_refill_form"):
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                with col_r1: added_qty = st.number_input("الكمية المضافة الجديدة للمخزن:", min_value=0.0, value=10.0, step=1.0)
                with col_r2: new_buy = st.number_input("سومة الشراء الجديدة الكلية (دج):", min_value=0.0, value=prod_refill[4])
                with col_r3: new_sell_box = st.number_input("سومة بيع العلبة / الجملة (دج):", min_value=0.0, value=prod_refill[5])
                with col_r4: new_sell_piece = st.number_input("سومة بيع القطعة/القارو تجزئة (دج):", min_value=0.0, value=prod_refill[6])
                
                if st.form_submit_button("💾 ضخ الحزمة الجديدة وتحديث الأسعار فوراً", use_container_width=True):
                    cursor.execute('''UPDATE products SET stock_box = stock_box + ?, buy_price_box = ?, sell_box = ?, sell_piece = ? WHERE barcode = ?''', 
                                   (added_qty, new_buy, new_sell_box, new_sell_piece, supply_barcode))
                    conn.commit()
                    st.success("✅ تم تحديث الكمية وتثبيت الأسعار الجديدة بنجاح في نظام الكاشير!")
                    st.rerun()

# ----------------- 3. المخزن وجرد السلع -----------------
with tab3:
    st.subheader("📥 تسجيل السلع الجديدة لأول مرة وتفقد الرفوف")
    with st.form("add_new_product_form"):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            b_code = st.text_input("باركود السلعة الجديدة (امسح بالقارئ):")
            p_name = st.text_input("اسم السلعة بالتفصيل:")
            u_type = st.selectbox("طريقة القياس والبيع الأساسية:", ["بالقطعة (وحدة/علبة)", "بالوزن (كيلوغرام)"])
            pieces_in_box = st.number_input("عدد القطع/القارو داخل العلبة الواحدة (20 للسجائر، و1 للمواد العادية):", min_value=1, value=1)
        with col_m2:
