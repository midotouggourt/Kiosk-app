import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

void main() {
  runApp(const CloudCashierApp());
}

class CloudCashierApp extends StatelessWidget {
  const CloudCashierApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'كاشير الكشك السحابي',
      theme: ThemeData(primarySwatch: Colors.blueGrey),
      home: const MainNavigationScreen(),
    );
  }
}

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({Key? key}) : super(key: key);

  @override
  _MainNavigationScreenState createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _selectedIndex = 0;
  List<Map<String, dynamic>> currentCart = [];
  bool printInvoiceOpt = true;
  static List<Map<String, dynamic>> savedInvoices = [];

  List<Widget> _getScreens() {
    return [
      SalesScreen(
        cart: currentCart,
        printOpt: printInvoiceOpt,
        onCartChanged: (updatedCart) => setState(() => currentCart = updatedCart),
        onPrintOptChanged: (val) => setState(() => printInvoiceOpt = val),
        onCheckout: processCheckout,
        hasLastInvoice: savedInvoices.isNotEmpty,
      ),
      const InventoryScreen(),
      const SuppliersScreen(),
      ReportsScreen(invoices: savedInvoices),
    ];
  }

  void processCheckout() {
    if (currentCart.isEmpty) return;
    String invId = 'INV-${DateTime.now().millisecondsSinceEpoch.toString().substring(7)}';
    double total = currentCart.fold(0, (sum, item) => sum + item['total']);
    double profit = currentCart.fold(0, (sum, item) => sum + item['profit']);

    setState(() {
      savedInvoices.add({
        'id': invId,
        'total': total,
        'profit': profit,
        'time': DateTime.now().toString().substring(0, 16),
      });
      currentCart.clear();
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('تم تأكيد البيع وحفظ الفاتورة $invId سحابياً!')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('كاشير الكشك السحابي ☁️', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
        backgroundColor: const Color(0xFF2c3e50),
        centerTitle: true,
      ),
      body: _getScreens()[_selectedIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        type: BottomNavigationBarType.fixed,
        selectedItemColor: Colors.blueAccent,
        unselectedItemColor: Colors.grey,
        onTap: (index) => setState(() => _selectedIndex = index),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.shopping_cart), label: 'الكاشير'),
          BottomNavigationBarItem(icon: Icon(Icons.add_business), label: 'الشراء'),
          BottomNavigationBarItem(icon: Icon(Icons.inventory), label: 'المخزون'),
          BottomNavigationBarItem(icon: Icon(Icons.bar_chart), label: 'التقارير'),
        ],
      ),
    );
  }
}

class SalesScreen extends StatelessWidget {
  final List<Map<String, dynamic>> cart;
  final bool printOpt;
  final ValueChanged<List<Map<String, dynamic>>> onCartChanged;
  final ValueChanged<bool> onPrintOptChanged;
  final VoidCallback onCheckout;
  final bool hasLastInvoice;

  const SalesScreen({
    Key? key, required this.cart, required this.printOpt,
    required this.onCartChanged, required this.onPrintOptChanged, required this.onCheckout, required this.hasLastInvoice,
  }) : super(key: key);

  double get totalAmount => cart.fold(0, (sum, item) => sum + item['total']);

  void addSmartItem(Map<String, dynamic> product, bool isBarcode) {
    List<Map<String, dynamic>> updated = List.from(cart);
    double price;
    String unit;
    double profit;

    if (isBarcode || product['click_unit'] == 'علبة') {
      price = (product['pr_pack'] ?? 0.0).toDouble();
      unit = 'علبة';
      profit = price - (product['buy_price'] ?? 0.0).toDouble();
    } else if (product['click_unit'] == 'كلغ') {
      price = (product['pr_pack'] ?? 0.0).toDouble() * 0.5; // محاكاة بيع رطل تلقائي
      unit = 'رطل';
      profit = (product['pr_pack'] - product['buy_price']) * 0.5;
    } else {
      price = (product['pr_piece'] ?? 0.0).toDouble();
      unit = 'ڨارو';
      double buyPricePiece = (product['buy_price'] ?? 0.0).toDouble() / (product['qty_pieces'] ?? 20);
      profit = price - buyPricePiece;
    }

    updated.add({
      'name': product['name'],
      'qty': unit == 'رطل' ? 0.5 : 1.0,
      'unit': unit,
      'total': price,
      'profit': profit,
    });
    onCartChanged(updated);
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth > 768) {
          return Row(
            children: [
              Expanded(flex: 3, child: _buildCartSection()),
              const VerticalDivider(width: 1, color: Colors.grey),
              Expanded(flex: 2, child: _buildCloudProductsSection()),
            ],
          );
        } else {
          return Column(
            children: [
              Expanded(flex: 3, child: _buildCartSection()),
              const Divider(height: 1, color: Colors.grey),
              Expanded(flex: 2, child: _buildCloudProductsSection()),
            ],
          );
        }
      },
    );
  }

  Widget _buildCartSection() {
    return Container(
      padding: const EdgeInsets.all(10),
      child: Column(
        children: [
          const Text('الفاتورة الحالية', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          Expanded(
            child: cart.isEmpty
                ? const Center(child: Text('السلة فارغة. اضغط على السلع للبيع الفوري'))
                : ListView.builder(
                    itemCount: cart.length,
                    itemBuilder: (context, i) => Card(
                      child: ListTile(
                        title: Text(cart[i]['name']),
                        subtitle: Text('${cart[i]['qty']} ${cart[i]['unit']} x ${cart[i]['total'] / cart[i]['qty']} دج'),
                        trailing: Text('${cart[i]['total']} دج', style: const TextStyle(fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ),
          ),
          const Divider(),
          Row(
            mainAxisAlignment: MainAxisAlignment.between,
            children: [
              const Text('المجموع الإجمالي:', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              Text('$totalAmount دج', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.green)),
            ],
          ),
          CheckboxListTile(
            title: const Text('طباعة حرارية اختيارية', style: TextStyle(fontSize: 12)),
            value: printOpt,
            onChanged: (val) => onPrintOptChanged(val!),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.green, minimumSize: const Size(double.infinity, 45)),
            onPressed: cart.isEmpty ? null : onCheckout,
            child: const Text('تأكيد وحفظ العملية السحابية', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          )
        ],
      ),
    );
  }

  Widget _buildCloudProductsSection() {
    return Container(
      color: const Color(0xFFf8f9fa),
      padding: const EdgeInsets.all(10),
      child: Column(
        children: [
          const Text('السلع الحية من السيرفر السحابي', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          Expanded(
            child: StreamBuilder<QuerySnapshot>(
              stream: FirebaseFirestore.instance.collection('products').snapshots(),
              builder: (context, snapshot) {
                if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
                final docs = snapshot.data!.docs;
                if (docs.isEmpty) return const Center(child: Text('المخزون فارغ بالسحابة'));
                return GridView.builder(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2, childAspectRatio: 2.2, crossAxisSpacing: 5, mainAxisSpacing: 5
                  ),
                  itemCount: docs.length,
                  itemBuilder: (context, i) {
                    var prod = docs[i].data() as Map<String, dynamic>;
                    String pName = prod['name'] ?? 'بدون اسم';
                    double displayPrice = prod['click_unit'] == 'كلغ'
                        ? (prod['pr_pack'] ?? 0.0).toDouble()
                        : (prod['pr_piece'] ?? 0.0).toDouble();
                    return ElevatedButton(
                      style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF34495e)),
                      onPressed: () => addSmartItem(prod, false),
                      child: Text('$pName\n($displayPrice دج)', textAlign: Center, style: const TextStyle(color: Colors.white, fontSize: 11)),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class InventoryScreen extends StatelessWidget {
  const InventoryScreen({Key? key}) : super(key: key);
  @override
  Widget build(BuildContext context) { return const Center(child: Text('إدارة الجرد والمخزون اليدوي')); }
}

class SuppliersScreen extends StatelessWidget {
  const SuppliersScreen({Key? key}) : super(key: key);
  @override
  Widget build(BuildContext context) { return const Center(child: Text('سجل الموردين والديون')); }
}

class ReportsScreen extends StatelessWidget {
  final List<Map<String, dynamic>> invoices;
  const ReportsScreen({Key? key, required this.invoices}) : super(key: key);
  @override
