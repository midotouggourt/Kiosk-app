import 'package:flutter/material.dart';

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
      theme: ThemeData(
        primarySwatch: Colors.blueGrey,
      ),
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

  // مخزن البيانات اليدوي المؤقت لجلسة العمل
  static List<Map<String, dynamic>> localInventory = [
    {'id': 1, 'name': 'علبة سجائر (جملة)', 'buy': 250.0, 'sell': 300.0, 'unit': 'جملة'},
    {'id': 2, 'name': 'سيجارة فردية (قطعة)', 'buy': 15.0, 'sell': 20.0, 'unit': 'قطعة'},
    {'id': 3, 'name': 'مادة بالوزن (كلغ)', 'buy': 200.0, 'sell': 240.0, 'unit': 'وزن'},
  ];

  static List<Map<String, dynamic>> savedInvoices = [];
  List<Map<String, dynamic>> currentCart = [];
  bool printInvoiceOpt = true;

  List<Widget> _getScreens() {
    return [
      SalesScreen(
        inventory: localInventory, 
        cart: currentCart, 
        printOpt: printInvoiceOpt,
        onCartChanged: (updatedCart) => setState(() => currentCart = updatedCart),
        onPrintOptChanged: (val) => setState(() => printInvoiceOpt = val),
        onCheckout: processCheckout,
        onReprint: reprintLastInvoice,
        hasLastInvoice: savedInvoices.isNotEmpty,
      ),
      InventoryScreen(
        inventory: localInventory,
        onProductAdded: (newProd) => setState(() => localInventory.add(newProd)),
      ),
      const SuppliersScreen(),
      ReportsScreen(invoices: savedInvoices),
    ];
  }

  void processCheckout() {
    if (currentCart.isEmpty) return;

    double total = currentCart.fold(0, (sum, item) => sum + item['total']);
    double profit = currentCart.fold(0, (sum, item) => sum + item['profit']);
    String invId = 'INV-${DateTime.now().millisecondsSinceEpoch.toString().substring(7)}';

    setState(() {
      savedInvoices.add({
        'id': invId,
        'total': total,
        'profit': profit,
        'time': DateTime.now().toString().substring(0, 16),
        'items': List.from(currentCart),
      });
      currentCart.clear();
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(printInvoiceOpt ? 'تم حفظ الفاتورة $invId وطباعتها حرارياً!' : 'تم حفظ الفاتورة $invId محلياً.')),
    );
  }

  void reprintLastInvoice() {
    if (savedInvoices.isEmpty) return;
    final last = savedInvoices.last;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('إعادة طباعة الفاتورة: ${last['id']}')),
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

// 1. شاشة المبيعات المتجاوبة مع حجم التابلت والكمبيوتر لمنع التمرير
class SalesScreen extends StatelessWidget {
  final List<Map<String, dynamic>> inventory;
  final List<Map<String, dynamic>> cart;
  final bool printOpt;
  final ValueChanged<List<Map<String, dynamic>>> onCartChanged;
  final ValueChanged<bool> onPrintOptChanged;
  final VoidCallback onCheckout;
  final VoidCallback onReprint;
  final bool hasLastInvoice;

  const SalesScreen({
    Key? key, required this.inventory, required this.cart, required this.printOpt,
    required this.onCartChanged, required this.onPrintOptChanged, required this.onCheckout,
    required this.onReprint, required this.hasLastInvoice,
  }) : super(key: key);

  double get totalAmount => cart.fold(0, (sum, item) => sum + item['total']);

  void addItem(Map<String, dynamic> prod, double qty) {
    List<Map<String, dynamic>> updated = List.from(cart);
    double total = prod['sell'] * qty;
    double profit = (prod['sell'] - prod['buy']) * qty;
    
    updated.add({
      'name': prod['name'],
      'qty': qty,
      'unit': prod['unit'],
      'total': total,
      'profit': profit,
    });
    onCartChanged(updated);
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth > 600) {
          return Row(
            children: [
              Expanded(flex: 3, child: _buildCartSection(context)),
              const VerticalDivider(width: 1, color: Colors.grey),
              Expanded(flex: 2, child: _buildProductsSection()),
            ],
          );
        } else {
          return Column(
            children: [
              Expanded(flex: 3, child: _buildCartSection(context)),
              const Divider(height: 1, color: Colors.grey),
              Expanded(flex: 2, child: _buildProductsSection()),
            ],
          );
        }
      },
    );
  }

  Widget _buildCartSection(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      child: Column(
        children: [
          const Text('الفاتورة الحالية', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          Expanded(
            child: cart.isEmpty 
              ? const Center(child: Text('السلة فارغة.'))
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
              const Text('المجموع:', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              Text('$totalAmount دج', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.green)),
            ],
          ),
          CheckboxListTile(
            title: const Text('طباعة حرارية اختيارية', style: TextStyle(fontSize: 12)),
            value: printOpt,
            onChanged: (val) => onPrintOptChanged(val!),
          ),
          Row(
            children: [
              Expanded(
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                  onPressed: cart.isEmpty ? null : onCheckout,
                  child: const Text('تأكيد البيع', style: TextStyle(color: Colors.white)),
                ),
              ),
              const SizedBox(width: 5),
              ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: Colors.orange),
                onPressed: hasLastInvoice ? onReprint : null,
                child: const Icon(Icons.print, color: Colors.white),
              ),
            ],
          )
        ],
      ),
    );
  }

  Widget _buildProductsSection() {
    return Container(
      color: const Color(0xFFf8f9fa),
      padding: const EdgeInsets.all(10),
      child: Column(
        children: [
          const Text('السلع المتاحة', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          Expanded(
            child: GridView.builder(
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2, childAspectRatio: 2.2, crossAxisSpacing: 5, mainAxisSpacing: 5
              ),
              itemCount: inventory.length,
              itemBuilder: (context, i) {
                final prod = inventory[i];
                return ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF34495e)),
                  onPressed: () => addItem(prod, prod['unit'] == 'وزن' ? 0.5 : 1.0),
                  child: Text('${prod['name']}\n(${prod['sell']} دج)', textAlign: Center, style: const TextStyle(color: Colors.white, fontSize: 11)),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

// 2. شاشة المخزون اليدوي والتصوير
class InventoryScreen extends StatefulWidget {
  final List<Map<String, dynamic>> inventory;
  final ValueChanged<Map<String, dynamic>> onProductAdded;

  const InventoryScreen({Key? key, required this.inventory, required this.onProductAdded}) : super(key: key);

  @override
  _InventoryScreenState createState() => _InventoryScreenState();
}

class _InventoryScreenState extends State<InventoryScreen> {
  final _nameCtrl = TextEditingController();
  final _buyCtrl = TextEditingController();
  final _sellCtrl = TextEditingController();
  String _selectedUnit = 'قطعة';

  void _saveProduct() {
