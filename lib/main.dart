import 'package:flutter/material.dart';
// مكتبة الاتصال السحابي بـ Firebase
import 'package:cloud_firestore/cloud_firestore.dart'; 

// دالة جلب المنتجات السحابية حياً من السيرفر (StreamBuilder)
Widget buildCloudProductsGrid() {
  return StreamBuilder<QuerySnapshot>(
    // الاتصال بجدول products الذي أنشأته يدوياً في Firebase
    stream: FirebaseFirestore.instance.collection('products').snapshots(),
    builder: (context, snapshot) {
      if (snapshot.hasError) {
        return const Center(child: Text('خطأ في الاتصال بالسحابة ❌'));
      }
      if (snapshot.connectionState == ConnectionState.waiting) {
        return const Center(child: CircularProgressIndicator()); // مؤشر تحميل لحين جلب البيانات
      }

      // جلب قائمة المنتجات السحابية الحقيقية
      final cloudProducts = snapshot.data!.docs;

      return GridView.builder(
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2, 
          childAspectRatio: 2.2, 
          crossAxisSpacing: 5, 
          mainAxisSpacing: 5
        ),
        itemCount: cloudProducts.length,
        itemBuilder: (context, i) {
          // قراءة بيانات كل سلعة من الحقول التي أنشأتها يدوياً
          var product = cloudProducts[i].data() as Map<String, dynamic>;
          String name = product['name'] ?? 'منتج بدون اسم';
          
          // قراءة سعر بيع الوحدة بناءً على نوع السلعة (سجائر أو وزن)
          double sellPrice = product['click_unit'] == 'كلغ' 
              ? (product['pr_pack'] ?? 0.0).toDouble() 
              : (product['pr_piece'] ?? 0.0).toDouble();

          return ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF34495e)),
            onPressed: () {
              // عند الضغط على المنتج من التابلت
              if (product['click_unit'] == 'كلغ') {
                // إذا كانت مادة بالوزن مثل الكاوكاو -> استدعاء دالة البيع بالوزن (مثال: رطل 0.5)
                handleWeightSale(product, 0.5); 
              } else {
                // إذا كانت سجائر -> استدعاء دالة البيع السريع بالڨارو (الحبة)
                handleSmartSale(product, isBarcodeScan: false);
              }
            },
            child: Text(
              '$name\n($sellPrice دج)', 
              textAlign: TextAlign.center, 
              style: const TextStyle(color: Colors.white, fontSize: 11)
            ),
          );
        },
      );
    },
  );
}
