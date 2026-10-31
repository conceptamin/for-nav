// for nav 근로자 앱의 호스트. 화면은 모두 WebView 안의 웹(app-front/)이고, 여기는 그 껍데기다.
// 불러올 주소는 코드에 적지 않고 --dart-define=APP_URL=로 받는다(app/README.md "실행").

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'host_page.dart';

const String appUrl = String.fromEnvironment('APP_URL');

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  runApp(const ForNavApp());
}

class ForNavApp extends StatelessWidget {
  const ForNavApp({super.key});

  @override
  Widget build(BuildContext context) {
    final appUri = Uri.tryParse(appUrl);
    final valid = appUri != null && (appUri.scheme == 'http' || appUri.scheme == 'https') && appUri.host.isNotEmpty;
    return AnnotatedRegion<SystemUiOverlayStyle>(
      // 밝은 배경 기준: 어두운 글자, 투명한 상태 표시줄(웹이 그 아래까지 그린다)
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        statusBarBrightness: Brightness.light,
        systemNavigationBarColor: Colors.transparent,
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
      child: MaterialApp(
        title: 'for nav',
        debugShowCheckedModeBanner: false,
        home: valid ? HostPage(appUri: appUri) : const _MissingAppUrl(),
      ),
    );
  }
}

/// 개발자가 APP_URL을 빠뜨렸을 때만 보인다
class _MissingAppUrl extends StatelessWidget {
  const _MissingAppUrl();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text('APP_URL이 없습니다.\nfvm flutter run --dart-define=APP_URL=http://localhost:5181'),
        ),
      ),
    );
  }
}
