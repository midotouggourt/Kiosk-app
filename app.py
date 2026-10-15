import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
from PIL import Image

# 1. إعداد واجهة مضغوطة مخصصة كلياً لمقاس شاشة التابلت بدون تمرير للأسفل
st.set_page_config(page_title="كاشير الكشك Pro", layout="wide", initial_sidebar_state="collapsed")

# تقليص المسافات العلوية والهوامش لجعل كل شيء يظهر في شاشة واحدة
st.markdown("""
    <style>
        .block-container {padding-top: 0.5rem; padding-bottom: 0.5rem; padding-left: 1rem; padding-right: 1rem;}
        h1 {margin-bottom: 0.2rem; padding-bottom: 0px;}
        .stTabs [data-baseweb="tab-list"] {gap: 4px;}
        .stTabs [data-baseweb="tab"] {padding: 6px 10px; font-size: 14px;}
    </style>
""", unsafe_allow_html=True)

# الاتصال بقاعدة البيانات السحابية وتفعيل دعم الصور الحقيقية (BLOB)
conn = sqlite3.connect("kiosk_cloud_db.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
cursor.execute("CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, company TEXT)")
cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                  (barcode TEXT PRIMARY KEY, name TEXT, category_id INTEGER, unit_type TEXT, 
                   buy_price_box REAL, sell_box REAL, sell_piece REAL, pieces_per_box INTEGER, stock_box REAL, min_stock REAL, image_blob BLOB)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS sales 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT, name TEXT, category_name TEXT,
                   sale_type TEXT, qty REAL, total_price REAL, profit REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS debts 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, total_amount REAL, remaining REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

# إدخال فئة افتراضية
cursor.execute("INSERT OR IGNORE INTO categories (id, name) VALUES (1, 'عام / كشك')")
conn.commit()

if 'carts' not in st.session_state:
    st.session_state.carts = {f"🛒 زبون {i}": [] for i in range(1, 4)}

st.markdown("<h2 style='text-align: center; color: #1E88E5; margin:0px; padding:0px;'>🏪 نظام كاشير الكشك الذكي Pro</h2>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🛒 كاشير المبيعات السريعة", 
    "⚡ التموين والأسعار", 
    "📦 المخزن والسلع والصور", 
    "💵 سجل الكريدي", 
    "📊 الأرباح والفائدة"
])

cursor.execute("SELECT id, name FROM categories")
categories_list = cursor.fetchall()
categories_dict = {cat[1]: cat[0] for cat in categories_list}
categories_names = list(categories_dict.keys())

# ----------------- 1. كاشير المبيعات السريعة المضغوط لشاشة واحدة -----------------
with tab1:
    # تقسيم الشاشة هندسياً إلى جانبين متوازيين لمنع التمرير للأسفل
    col_left_cart, col_right_products = st.columns([4, 6])
    
    with col_right_products:
        st.markdown("##### 📦 المنتجات السريعة حسب العائلة")
        active_cart = st.selectbox("🎯 الحساب الحالي النشط:", list(st.session_state.carts.keys()), label_visibility="collapsed")
        
        # أزرار تصفية العائلات بشكل أفقي مدمج
        selected_filter_cat = st.radio("التصفية:", ["الكل"] + categories_names, horizontal=True, label_visibility="collapsed")
        
        if selected_filter_cat == "الكل":
            cursor.execute("SELECT * FROM products")
        else:
            cat_id = categories_dict[selected_filter_cat]
            cursor.execute("SELECT * FROM products WHERE category_id=?", (cat_id,))
        all_visible_products = cursor.fetchall()
        
        # عرض السلع في شبكة من 3 أعمدة مضغوطة تناسب حجم أزرار الكاشير الاحترافية
        if all_visible_products:
            p_cols = st.columns(3)
            for idx, prod_item in enumerate(all_visible_products):
                with p_cols[idx % 3]:
                    st.markdown(f"<div style='background-color:#F8F9FA; padding:4px; border-radius:6px; text-align:center; border: 1px solid #DEE2E6; margin-bottom:2px;'>", unsafe_allow_html=True)
                    
                    # عرض الصورة الحقيقية للمنتج إذا تم التقاطها بالكاميرا
                    if prod_item[10]:
                        try:
                            img = Image.open(io.BytesIO(prod_item[10]))
                            st.image(img, width=60)
                        except: st.markdown("<span style='font-size:20px;'>📦</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='font-size:20px;'>📦</span>", unsafe_allow_html=True)
                        
                    st.markdown(f"<p style='margin:2px 0; font-size:13px; font-weight:bold;'>{prod_item[1]}</p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#1E88E5; font-size:11px; margin:0;'>علبة: {prod_item[5]}دج | قارو: {prod_item[6]}دج</p></div>", unsafe_allow_html=True)
                    
                    b_type = st.selectbox("النوع:", ["بالعلبة", "بالقارو"] if prod_item[7] > 1 else ["وحدة", "كغ"], key=f"bt_{idx}_{prod_item[0]}_{active_cart}", label_visibility="collapsed")
                    
                    if st.button(f"➕ {prod_item[1][:10]}", key=f"sb_{idx}_{prod_item[0]}_{active_cart}", use_container_width=True):
                        if "علبة" in b_type or "وحدة" in b_type:
                            final_p, stock_ded, net_profit = prod_item[5], 1.0, (prod_item[5] - prod_item[4])
                        else:
                            final_p, stock_ded, net_profit = prod_item[6], 1.0 / prod_item[7], (prod_item[6] - (prod_item[4]/prod_item[7]))
                            
                        st.session_state.carts[active_cart].append({
                            'barcode': prod_item[0], 'name': prod_item[1], 'type': b_type, 'qty': 1.0, 'price': final_p, 'total': final_p, 'profit': net_profit, 'deduction': stock_ded
                        })
                        st.rerun()
        
        # باركود وبحث يدوي احتياطي مدمج
        barcode_scan = st.text_input("امسح باركود أو اكتب الاسم للبحث السريع:", key=f"sc_{active_cart}", placeholder="امسح بالمسدس هنا...")
        if barcode_scan:
            cursor.execute("SELECT * FROM products WHERE barcode=? OR name LIKE ?", (barcode_scan, f"%{barcode_scan}%"))
            p_res = cursor.fetchone()
            if p_res:
                if st.button(f"🛒 إضافة السلعة المبحوث عنها: {p_res[1]}", use_container_width=True, key=f"add_sc_{p_res[0]}_{active_cart}"):
                    st.session_state.carts[active_cart].append({
                        'barcode': p_res[0], 'name': p_res[1], 'type': "بالعلبة", 'qty': 1.0, 'price': p_res[5], 'total': p_res[5], 'profit': (p_res[5]-p_res[4]), 'deduction': 1.0
                    })
                    st.rerun()

    with col_left_cart:
        st.markdown(f"##### 🛒 سلة مبيعات الحساب")
        if st.session_state.carts[active_cart]:
            df_cart = pd.DataFrame(st.session_state.carts[active_cart])
            # عرض جدول مبيعات مدمج صغير يتناسب مع شاشة واحدة
            st.dataframe(df_cart[['name', 'type', 'total']], use_container_width=True, height=180)
            cart_total = df_cart['total'].sum()
            st.markdown(f"### 💰 الحساب الكلي: <span style='color:#2E7D32;'>{cart_total:,} دج</span>", unsafe_allow_html=True)
            
            pay_method = st.radio("الدفع للصندوق:", ["كاش نقداً", "كريدي مؤجل"], horizontal=True)
            customer_name = st.text_input("اسم الزبون المدين:", key=f"c_name_{active_cart}", placeholder="اكتب الاسم هنا...") if "كريدي" in pay_method else ""
            
            if st.button("🚀 تأكيد وحفظ العملية فورا وبدون طباعة تلقائية", type="primary", use_container_width=True, key=f"conf_{active_cart}"):
                if "كريدي" in pay_method and customer_name:
                    cursor.execute("INSERT INTO debts (customer_name, total_amount, remaining) VALUES (?, ?, ?)", (customer_name, cart_total, cart_total))
                for item in st.session_state.carts[active_cart]:
                    cursor.execute("INSERT INTO sales (barcode, name, category_name, sale_type, qty, total_price, profit) VALUES (?, ?, 'كشك', ?, ?, ?, ?)",
                                   (item['barcode'], item['name'], item['type'], item['qty'], item['total'], item['profit']))
                    cursor.execute("UPDATE products SET stock_box = stock_box - ? WHERE barcode = ?", (item['deduction'], item['barcode']))
                conn.commit()
                st.session_state.carts[active_cart] = []
                st.success("✅ تم حفظ العملية وتصفير السلة!")
                st.rerun()
        else:
            st.info("السلة فارغة حالياً. اضغط على المنتجات في اليمين لتعبئتها فورا بلمسة واحدة.")

# ----------------- 3. المخزن وتفعيل ميزة تصوير المنتوج الحقيقي بالكاميرا -----------------
with tab3:
    st.subheader("📥 تسجيل السلع الجديدة لأول مرة وتصويرها")
    with st.form("add_product_camera_form"):
        col_inp, col_cam = st.columns([6, 4])
        with col_inp:
            b_code = st.text_input("باركود السلعة الجديدة (امسح بالمسدس):")
            p_name = st.text_input("اسم السلعة بالتفصيل (مثال: روثمانز رمادي):")
            chosen_cat_name = st.selectbox("اختر عائلة وصنف السلعة لتنظيم الأزرار:", categories_names)
            pieces_in_box = st.number_input("عدد السجائر/القطع داخل الصندوق الواحد:", min_value=1, value=20)
            cost_p = st.number_input("سعر شراء العلبة من المورد (دج):", min_value=0.0)
            box_p = st.number_input("سعر بيع العلبة كاملة (دج):", min_value=0.0)
            piece_p = st.number_input("سعر بيع القارو الواحد تجزئة (دج):", min_value=0.0)
            curr_stock = st.number_input("المخزون المتوفر حالياً بالعلب:", min_value=0.0)
            min_stock = st.number_input("حد تنبيه قرب النفاد:", min_value=1.0, value=5.0)
        with col_cam:
            st.markdown("📸 **التصوير المباشر للمنتج أو رفع صورته:**")
