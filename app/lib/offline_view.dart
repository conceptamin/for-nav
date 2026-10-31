// 앱 주소를 불러오지 못했을 때 WebView 오류 화면 대신 보이는 네이티브 안내 한 장.
// 번들(app-front backlog 05) 전까지의 임시 동작이다. 웹 화면이 없으므로 문구는 한국어·영어를 함께 쓰고,
// 응급은 네트워크를 기다리지 않으므로 119 전화를 여기에도 둔다.

import 'package:flutter/material.dart';

const _brand = Color(0xFF085E60); // frontend/src/styles.css --brand
const _danger = Color(0xFFCA1D13); // frontend/src/styles.css --danger
const _bg = Color(0xFFE3EFF0); // frontend/src/styles.css --bg

class OfflineView extends StatelessWidget {
  const OfflineView({super.key, required this.onRetry, required this.onCall119});

  final VoidCallback onRetry;
  final VoidCallback onCall119;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return ColoredBox(
      color: _bg,
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const Spacer(),
              const Icon(Icons.wifi_off_rounded, size: 56, color: _brand),
              const SizedBox(height: 16),
              Text('인터넷에 연결되지 않았습니다', style: text.titleLarge, textAlign: TextAlign.center),
              const SizedBox(height: 4),
              Text('No internet connection', style: text.bodyLarge, textAlign: TextAlign.center),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: onRetry,
                style: FilledButton.styleFrom(backgroundColor: _brand, minimumSize: const Size.fromHeight(52)),
                child: const Text('다시 시도 · Retry'),
              ),
              const Spacer(),
              FilledButton.icon(
                onPressed: onCall119,
                icon: const Icon(Icons.call),
                label: const Text('119 전화 · Call 119'),
                style: FilledButton.styleFrom(backgroundColor: _danger, minimumSize: const Size.fromHeight(52)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
