import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
from PIL import Image

# إعداد واجهة فائقة الانضغاط تناسب حجم أي تابلت بدون تمرير
st.set_page_config(page_title="كاشير الكشك Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        .block-container {padding-top: 0.2rem; padding-bottom: 0.2rem; padding-left: 0.5rem; padding-right: 0.5rem;}
        h2, h3 {margin-top: 0px; margin-bottom: 2px; padding:0px;}
        .stButton button {padding: 4px 10px; font-size: 13px;}
        .stForm {padding: 10px; border-radius: 8px;}
    </style>
""", unsafe_allow_html=True)

conn = sqlite3.connect("kiosk_cloud_db.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                  (barcode TEXT PRIMARY KEY, name TEXT, category_id INTEGER, unit_type TEXT, 
                   buy_price_box REAL, sell_box REAL, sell_piece REAL, pieces_per_box INTEGER, stock_box REAL, min_stock REAL, image_blob BLOB)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS sales 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT, name TEXT, category_name TEXT,
                   sale_type TEXT, qty REAL, total_price REAL, profit REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS debts 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, total_amount REAL, remaining REAL, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

cursor.execute("INSERT OR IGNORE INTO categories (id, name) VALUES (1, 'عام / كشك')")
conn.commit()

if 'carts' not in st.session_state:
    st.session_state.carts = {f"🛒 زبون {i}": [] for i in range(1, 4)}

st.markdown("<h3 style='text-align: center; color: #1E88E5; margin:0;'>🏪 كاشير الكشك الرقمي المتكامل</h3>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🛒 كاشير المبيعات السريعة", 
    "⚡ التموين والأسعار", 
    "📦 المخزن وإدخال السلع", 
    "💵 سجل الكريدي", 
    "📊 الأرباح والفائدة"
])

cursor.execute("SELECT id, name FROM categories")
categories_list = cursor.fetchall()
categories_dict = {cat: cat for cat in categories_list}
categories_names = list(categories_dict.keys())

# ----------------- 1. كاشير المبيعات السريعة -----------------
with tab1:
    col_left_cart, col_right_products = st.columns([1, 1])
    
    with col_right_products:
        st.markdown("##### 📦 أزرار البيع السريع")
        active_cart = st.selectbox("الزبون:", list(st.session_state.carts.keys()), label_visibility="collapsed")
        selected_filter_cat = st.radio("التصفية:", ["الكل"] + categories_names, horizontal=True, label_visibility="collapsed")
        
        if selected_filter_cat == "الكل":
            cursor.execute("SELECT * FROM products")
        else:
            cat_id = categories_dict[selected_filter_cat]
            cursor.execute("SELECT * FROM products WHERE category_id=?", (cat_id,))
        all_visible_products = cursor.fetchall()
        
        if all_visible_products:
            p_cols = st.columns(3)
            for idx, prod_item in enumerate(all_visible_products):
                with p_cols[idx % 3]:
                    st.markdown(f"<div style='background-color:#F8F9FA; padding:4px; border-radius:6px; text-align:center; border: 1px solid #DEE2E6; margin-bottom:2px;'>", unsafe_allow_html=True)
                    if prod_item:
                        try:
                            img = Image.open(io.BytesIO(prod_item))
                            st.image(img, width=50)
                        except: st.markdown("<span style='font-size:16px;'>📦</span>", unsafe_allow_html=True)
                    else: st.markdown("<span style='font-size:16px;'>📦</span>", unsafe_allow_html=True)
                        
                    st.markdown(f"<p style='margin:1px 0; font-size:12px; font-weight:bold;'>{prod_item}</p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#1E88E5; font-size:10px; margin:0;'>علبة: {prod_item}دج | قارو: {prod_item}دج</p></div>", unsafe_allow_html=True)
                    
                    b_type = st.selectbox("النوع:", ["بالعلبة", "بالقارو"] if prod_item > 1 else ["وحدة", "كغ"], key=f"bt_{idx}_{prod_item}_{active_cart}", label_visibility="collapsed")
                    
                    if st.button(f"➕ {prod_item[:8]}", key=f"sb_{idx}_{prod_item}_{active_cart}", use_container_width=True):
                        final_p = prod_item if "علبة" in b_type or "وحدة" in b_type else prod_item
                        stock_ded = 1.0 if "علبة" in b_type or "وحدة" in b_type else 1.0 / prod_item
                        net_profit = (prod_item - prod_item) if "علبة" in b_type or "وحدة" in b_type else (prod_item - (prod_item/prod_item))
                            
                        st.session_state.carts[active_cart].append({
                            'barcode': prod_item, 'name': prod_item, 'type': b_type, 'qty': 1.0, 'price': final_p, 'total': final_p, 'profit': net_profit, 'deduction': stock_ded
                        })
                        st.rerun()
        
        barcode_scan = st.text_input("البحث السريع بالباركود أو الاسم:", key=f"sc_{active_cart}", placeholder="امسح هنا للبيع الفوري...")
        if barcode_scan:
            cursor.execute("SELECT * FROM products WHERE barcode=? OR name LIKE ?", (barcode_scan, f"%{barcode_scan}%"))
            p_res = cursor.fetchone()
            if p_res:
                if st.button(f"🛒 إضافة المبحوث عنه: {p_res}", use_container_width=True, key=f"add_sc_{p_res}_{active_cart}"):
                    st.session_state.carts[active_cart].append({
                        'barcode': p_res, 'name': p_res, 'type': "بالعلبة", 'qty': 1.0, 'price': p_res, 'total': p_res, 'profit': (p_res-p_res), 'deduction': 1.0
                    })
                    st.rerun()

    with col_left_cart:
        st.markdown("##### 🛒 سلة المبيعات")
        if st.session_state.carts[active_cart]:
            df_cart = pd.DataFrame(st.session_state.carts[active_cart])
            st.dataframe(df_cart[['name', 'type', 'total']], use_container_width=True, height=130)
            cart_total = df_cart['total'].sum()
            st.markdown(f"#### 💰 الحساب: <span style='color:#2E7D32;'>{cart_total:,} دج</span>", unsafe_allow_html=True)
            
            pay_method = st.radio("الدفع:", ["كاش", "كريدي"], horizontal=True)
            customer_name = st.text_input("اسم الزبون:", key=f"c_name_{active_cart}") if "كريدي" in pay_method else ""
            
            if st.button("🚀 حفظ وتأكيد البيع", type="primary", use_container_width=True, key=f"conf_{active_cart}"):
                if "كريدي" in pay_method and customer_name:
                    cursor.execute("INSERT INTO debts (customer_name, total_amount, remaining) VALUES (?, ?, ?)", (customer_name, cart_total, cart_total))
                for item in st.session_state.carts[active_cart]:
                    cursor.execute("INSERT INTO sales (barcode, name, category_name, sale_type, qty, total_price, profit) VALUES (?, ?, 'كشك', ?, ?, ?, ?)",
                                   (item['barcode'], item['name'], item['type'], item['qty'], item['total'], item['profit']))
                    cursor.execute("UPDATE products SET stock_box = stock_box - ? WHERE barcode = ?", (item['deduction'], item['barcode']))
                conn.commit()
                st.session_state.carts[active_cart] = []
                st.success("✅ تم حفظ العملية!")
                st.rerun()

# ----------------- 3. المخزن وجرد السلع الفوق مضغوط -----------------
with tab3:
    st.subheader("📦 إضافة السلع للمخزن العام")
    with st.form("add_product_compact_form"):
        # تقسيم استمارة المخزن هندسياً لعرض كل شيء دفعة واحدة في الشاشة
        c_i1, c_i2 = st.columns(2)
        with c_i1:
            b_code = st.text_input("باركود السلعة (امسح بالقارئ):")
            p_name = st.text_input("اسم السلعة بالتفصيل:")
            chosen_cat_name = st.selectbox("عائلة السلعة:", categories_names)
            pieces_in_box = st.number_input("عدد السجائر/القطع في الصندوق:", min_value=1, value=20)
        with c_i2:
            cost_p = st.number_input("سعر شراء العلبة (دج):", min_value=0.0)
            box_p = st.number_input("سعر بيع العلبة (دج):", min_value=0.0)
            piece_p = st.number_input("سعر بيع القارو تجزئة (دج):", min_value=0.0)
            curr_stock = st.number_input("المخزون الحالي بالعلب:", min_value=0.0)
            min_stock = st.number_input("حد التنبيه للنقص:", min_value=1.0, value=5.0)
        
        # جعل ميزة الصورة اختيارية تماماً وبسيطة عبر زر تحميل لكي لا تعطل الاستمارة
        st.markdown("📸 **إضافة صورة للمنتج (اختياري):**")
        uploaded_file = st.file_uploader("اختر صورة السلعة من المعرض أو التقطها:", type=["png", "jpg", "jpeg"])

        # زر الحفظ يظهر الآن كبيراً وواضحاً في الشاشة مباشرة وبدون تمرير
        if st.form_submit_button("💾 حفظ السلعة الجديدة وتفعيل زر اللمس فوراً", use_container_width=True):
            if b_code and p_name:
                img_byte_arr = None
                if uploaded_file:
                    img = Image.open(uploaded_file)
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    img_byte_arr = img_byte_arr.getvalue()
                
                cat_id_final = categories_dict[chosen_cat_name]
                cursor.execute("INSERT OR REPLACE INTO products (barcode, name, category_id, unit_type, buy_price_box, sell_box, sell_piece, pieces_per_box, stock_box, min_stock, image_blob) VALUES (?, ?, ?, 'قطعة', ?, ?, ?, ?, ?, ?, ?)",
                               (b_code, p_name, cat_id_final, cost_p, box_p, piece_p, int(pieces_in_box), curr_stock, min_stock, img_byte_arr))
                conn.commit()
