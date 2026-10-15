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

# إدخال فئة افتراضية لتجنب تجميد التسجيل لمرة واحدة
cursor.execute("INSERT OR IGNORE INTO categories (id, name) VALUES (1, 'عام / كشك')")
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

# جلب الفئات المتاحة لربطها في الواجهات
cursor.execute("SELECT id, name FROM categories")
categories_list = cursor.fetchall()
categories_dict = {cat[1]: cat[0] for cat in categories_list}
categories_names = list(categories_dict.keys())

# ----------------- 1. كاشير المبيعات السريعة (المطور بالكامل بالأزرار والصور) -----------------
with tab1:
    st.subheader("⚡ نقطة البيع السريع بلمس الأزرار والبارود")
    active_cart = st.selectbox("📌 اختر الزبون الحالي النشط للحساب:", list(st.session_state.carts.keys()))
    
    # واجهة التصفية عبر عائلات المنتجات
    selected_filter_cat = st.radio("📂 تصفية المنتجات حسب العائلة المنسدلة:", ["الكل"] + categories_names, horizontal=True)
    
    st.markdown("---")
    st.markdown("#### 🛍️ أزرار المنتجات السريعة (اضغط بلمسة واحدة للبيع الفوري):")
    
    # جلب المنتجات حسب التصفية المحددة للعائلة
    if selected_filter_cat == "الكل":
        cursor.execute("SELECT * FROM products")
    else:
        cat_id = categories_dict[selected_filter_cat]
        cursor.execute("SELECT * FROM products WHERE category_id=?", (cat_id,))
    all_visible_products = cursor.fetchall()
    
    if all_visible_products:
        # عرض المنتجات كأزرار ملونة تفاعلية وبطاقات لمسية داخل شبكة هندسية
        cols = st.columns(4)
        for idx, prod_item in enumerate(all_visible_products):
            with cols[idx % 4]:
                st.markdown(f"""
                <div style='background-color:#F5F5F5; padding:10px; border-radius:10px; text-align:center; border: 1px solid #E0E0E0;'>
                    <span style='font-size:35px;'>📦</span>
                    <h5 style='margin:5px 0;'>{prod_item[1]}</h5>
                    <p style='color:#1E88E5; font-weight:bold; margin:0;'>علبة: {prod_item[5]} دج | قارو: {prod_item[6]} دج</p>
                </div>
                """, unsafe_allow_html=True)
                
                # تفعيل البيع المباشر عند النقر على الزر
                b_type = st.selectbox("نوع البيع:", ["بالعلبة كاملة/الجملة", "بالقارو / بالقطعة منفردة"] if prod_item[7] > 1 else ["بالقطعة (وحدة)", "بالوزن (كيلوغرام)"], key=f"btn_type_{idx}_{prod_item[0]}")
                b_qty = st.number_input("الكمية:", min_value=1.0, value=1.0, step=1.0, key=f"btn_qty_{idx}_{prod_item[0]}")
                
                if st.button(f"🛒 بيع {prod_item[1]}", key=f"sell_btn_{idx}_{prod_item[0]}", use_container_width=True):
                    if b_type == "بالعلبة كاملة/الجملة" or b_type == "بالقطعة (وحدة)":
                        final_p = prod_item[5]
                        stock_ded = b_qty
                        net_profit = (prod_item[5] - prod_item[4]) * b_qty
                    elif b_type == "بالقارو / بالقطعة منفردة":
                        final_p = prod_item[6]
                        stock_ded = b_qty / prod_item[7]
                        net_profit = (prod_item[6] - (prod_item[4]/prod_item[7])) * b_qty
                    else:
                        final_p = prod_item[5]
                        stock_ded = b_qty
                        net_profit = (prod_item[5] - prod_item[4]) * b_qty
                        
                    st.session_state.carts[active_cart].append({
                        'barcode': prod_item[0], 'name': prod_item[1], 'type': b_type, 'qty': b_qty, 'price': final_p, 'total': b_qty * final_p, 'profit': net_profit, 'deduction': stock_ded
                    })
                    st.success(f"✅ أضيف: {prod_item[1]}")
                    st.rerun()
    else:
        st.info("لا توجد منتجات مسجلة في هذه العائلة حالياً.")

    st.markdown("---")
    st.markdown("#### 🔍 أو ابحث بالباركود / الاسم يدوياً:")
    
    # اختيار أو مسح السلعة يدوياً
    cursor.execute("SELECT barcode, name FROM products")
    search_list = cursor.fetchall()
    search_options = {f"{item[1]} [{item[0]}]": item[0] for item in search_list}
    
    barcode_scan = st.text_input("امسح باركود السلعة بالقارئ هنا للبيع السريع:", key=f"scan_field_{active_cart}")
    manual_search = st.selectbox("أو اختر اسم السلعة يدوياً من هذه القائمة المنسدلة للبحث الحرفي:", [""] + list(search_options.keys()))
    
    final_search_barcode = ""
    if barcode_scan:
        final_search_barcode = barcode_scan.strip()
    elif manual_search:
        final_search_barcode = search_options[manual_search]
        
    if final_search_barcode:
        cursor.execute("SELECT * FROM products WHERE barcode=?", (final_search_barcode,))
        prod = cursor.fetchone()
        if prod:
            st.success(f"📦 السلعة النشطة للقارئ: **{prod[1]}** | المتوفر بالرفوف: {prod[8]:.2f} علبة")
            s_type = st.radio("اختر نوع البيع المطلوب للزبون الحين:", ["بالعلبة كاملة/الجملة", "بالقارو / بالقطعة منفردة"] if prod[7] > 1 else ["بالقطعة (وحدة)", "بالوزن (كيلوغرام)"], key=f"radio_search_{active_cart}")
            qty = st.number_input("الكمية المبيوعة:", min_value=0.01, value=1.0, key=f"qty_search_{active_cart}")
            
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
                
            if st.button("➕ إضافة هذا البحث للسلة", use_container_width=True, key=f"add_search_{active_cart}"):
                st.session_state.carts[active_cart].append({
                    'barcode': final_search_barcode, 'name': prod[1], 'type': s_type, 'qty': qty, 'price': price, 'total': qty * price, 'profit': profit, 'deduction': stock_deduction
                })
                st.rerun()

    # محتويات السلة وتأكيد الخزينة
    st.markdown("---")
    st.markdown(f"#### 🛒 جدول الفاتورة ومحتويات سلة: **{active_cart}**")
    if st.session_state.carts[active_cart]:
        df_cart = pd.DataFrame(st.session_state.carts[active_cart])
        st.dataframe(df_cart[['name', 'type', 'qty', 'price', 'total']], use_container_width=True)
        cart_total = df_cart['total'].sum()
        st.markdown(f"### 💰 إجمالي الحساب المطلوب للقص: {cart_total:,} دج")
        
        pay_method = st.selectbox("طريقة استلام المال للصندوق:", ["نقداً كاش", "كريدي دين مؤجل"])
        customer_name = st.text_input("اكتب اسم الزبون المدين لتسجيله بالكارني:") if pay_method == "كريدي دين مؤجل" else ""
        
        if st.button("🚀 تأكيد البيع النهائي وحفظ البون وطباعته", type="primary", use_container_width=True):
            if pay_method == "كريدي دين مؤجل" and customer_name:
                cursor.execute("INSERT INTO debts (customer_name, total_amount, remaining) VALUES (?, ?, ?)", (customer_name, cart_total, cart_total))
            for item in st.session_state.carts[active_cart]:
                cursor.execute("INSERT INTO sales (barcode, name, sale_type, qty, total_price, profit) VALUES (?, ?, ?, ?, ?, ?)",
                               (item['barcode'], item['name'], item['type'], item['qty'], item['total'], item['profit']))
                cursor.execute("UPDATE products SET stock_box = stock_box - ? WHERE barcode = ?", (item['deduction'], item['barcode']))
            conn.commit()
            st.session_state.carts[active_cart] = []
            st.success("✅ تم حفظ وفهرسة العملية بنجاح في ميزانية اليوم!")
            st.balloons()
            st.rerun()
    else:
        st.info("سلة البيع فارغة حالياً. اضغط على أزرار السلع أو امسح الباركود للبدء في تعبئة بون البيع.")
