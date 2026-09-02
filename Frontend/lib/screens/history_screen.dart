import 'package:flutter/material.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan History'),
        centerTitle: true,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          HistoryCard(
            productName: 'ABC Foods',
            date: '01 Sep 2026',
            status: 'Compliant',
            icon: Icons.check_circle,
            statusColor: Colors.green,
          ),
          HistoryCard(
            productName: 'XYZ Product',
            date: '01 Sep 2026',
            status: 'Violation Found',
            icon: Icons.cancel,
            statusColor: Colors.red,
          ),
          HistoryCard(
            productName: 'Sample Product',
            date: '31 Aug 2026',
            status: 'Manual Review',
            icon: Icons.warning,
            statusColor: Colors.orange,
          ),
        ],
      ),
    );
  }
}

class HistoryCard extends StatelessWidget {
  final String productName;
  final String date;
  final String status;
  final IconData icon;
  final Color statusColor;

  const HistoryCard({
    super.key,
    required this.productName,
    required this.date,
    required this.status,
    required this.icon,
    required this.statusColor,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: Icon(
          icon,
          color: statusColor,
          size: 35,
        ),
        title: Text(
          productName,
          style: const TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.bold,
          ),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text(
            date,
            style: const TextStyle(
              color: Colors.grey,
            ),
          ),
        ),
        trailing: Text(
          status,
          style: TextStyle(
            color: statusColor,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
}