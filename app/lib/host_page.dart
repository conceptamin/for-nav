// WebView 한 장과 호스트 계약의 호스트 쪽 구현(app-front/README.md "호스트 계약", app-front backlog 03).
// - ready를 받은 뒤에만 init을 보낸다. onPageFinished에서는 아무것도 하지 않는다.
// - 안전 영역(MediaQuery.padding)이 바뀌면(회전·크기 변경) insets를 다시 보낸다.
// - 앱 출처 밖 이동은 막고 외부 앱으로 연다. Android 뒤로 가기는 웹에 먼저 묻는다.
// - googleSignIn을 받으면 네이티브 Google 로그인(signOut → authenticate)의 ID 토큰을 googleSignInResult로 돌려준다(app-front backlog 06).
// - 로그에는 메시지 type만 남긴다. openExternal.url·이동 주소·메시지 본문·ID 토큰·계정 정보를 찍지 않는다.

import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_wkwebview/webview_flutter_wkwebview.dart';

import 'bridge.dart';
import 'navigation.dart';
import 'offline_view.dart';

/// Google OAuth 클라이언트 ID(--dart-define, app/README.md "Google 로그인"). 비밀값이 아니지만 코드에 적지 않는다.
/// 웹 클라이언트 ID는 서버 GOOGLE_CLIENT_ID와 같은 값이고, ID 토큰의 aud가 이것이 되게 serverClientId로 준다
const String googleWebClientId = String.fromEnvironment('GOOGLE_WEB_CLIENT_ID');
const String googleIosClientId = String.fromEnvironment('GOOGLE_IOS_CLIENT_ID');

class HostPage extends StatefulWidget {
  const HostPage({super.key, required this.appUri});

  /// 불러올 웹앱 주소(--dart-define=APP_URL). 이 주소의 출처가 "앱 안"이다
  final Uri appUri;

  @override
  State<HostPage> createState() => _HostPageState();
}

class _HostPageState extends State<HostPage> {
  late final WebViewController _controller;

  /// 웹이 ready를 보냈다. 이 뒤에만 init·insets를 보낸다
  bool _webReady = false;
  bool _offline = false;
  EdgeInsets? _padding;
  String _appVersion = '';

  final bool _signInEnabled = nativeSignInConfigured(
    isIOS: Platform.isIOS,
    webClientId: googleWebClientId,
    iosClientId: googleIosClientId,
  );
  Future<void>? _signInInit;

  /// 진행 중인 googleSignIn 번호. 더 새 요청이 오거나 페이지가 다시 ready하면 앞 결과는 버린다
  int _signInSeq = 0;
  bool _signInPending = false;

  @override
  void initState() {
    super.initState();
    PackageInfo.fromPlatform().then((info) => _appVersion = info.version);

    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.white)
      ..addJavaScriptChannel(channelName, onMessageReceived: _onMessage)
      ..setNavigationDelegate(
        NavigationDelegate(onNavigationRequest: _onNavigationRequest, onWebResourceError: _onWebResourceError),
      );

    final platform = _controller.platform;
    if (platform is WebKitWebViewController) {
      // iOS 뒤로 가기는 가장자리 스와이프다. 웹은 관여하지 않는다
      platform.setAllowsBackForwardNavigationGestures(true);
      platform.setInspectable(kDebugMode);
    }

    _controller.loadRequest(widget.appUri);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final padding = MediaQuery.paddingOf(context);
    if (padding == _padding) return;
    _padding = padding;
    if (_webReady) _post(insetsMessage(padding));
  }

  void _onMessage(JavaScriptMessage message) {
    final msg = parseMessage(message.message);
    if (msg == null) return;
    final type = msg['type'] as String;
    _log('← $type');
    switch (type) {
      case 'ready':
        _webReady = true;
        // 새로 불린 페이지는 앞 요청을 기다리지 않는다
        _signInSeq++;
        _signInPending = false;
        _sendInit();
      case 'openExternal':
        final url = msg['url'];
        if (url is String) _openExternal(url);
      case 'googleSignIn':
        if (_signInEnabled) _googleSignIn();
    }
  }

  Future<void> _sendInit() async {
    if (_appVersion.isEmpty) _appVersion = (await PackageInfo.fromPlatform()).version;
    if (!mounted) return;
    _post(
      initMessage(
        platform: Platform.isIOS ? 'ios' : 'android',
        appVersion: _appVersion,
        // Platform.localeName은 iOS에서 앱 번들이 지원하는 언어로 좁혀지므로 기기 첫 번째 언어(BCP-47)를 쓴다
        locale: PlatformDispatcher.instance.locale.toLanguageTag(),
        padding: _padding ?? MediaQuery.paddingOf(context),
        features: [if (_signInEnabled) featureGoogleSignIn],
      ),
    );
  }

  /// 늘 계정 선택이 뜨게 먼저 signOut한다(웹에서 로그아웃해도 호스트에는 Google 로그인이 남는다)
  Future<void> _googleSignIn() async {
    if (_signInPending) _post(googleSignInFailure(canceled: false));
    final seq = ++_signInSeq;
    _signInPending = true;
    Map<String, Object> result;
    try {
      await (_signInInit ??= GoogleSignIn.instance.initialize(
        clientId: Platform.isIOS ? googleIosClientId : null,
        serverClientId: googleWebClientId,
      )).catchError((Object e) {
        _signInInit = null;
        throw e;
      });
      await GoogleSignIn.instance.signOut();
      final account = await GoogleSignIn.instance.authenticate();
      final idToken = account.authentication.idToken;
      result = idToken == null || idToken.isEmpty ? googleSignInFailure(canceled: false) : googleSignInSuccess(idToken);
    } on Object catch (e) {
      // 예외 메시지에 계정 정보가 들 수 있어 종류만 남긴다
      _log('googleSignIn 실패(${e is GoogleSignInException ? e.code.name : e.runtimeType})');
      result = googleSignInFailure(canceled: isSignInCanceled(e));
    }
    if (seq != _signInSeq || !mounted) return;
    _signInPending = false;
    _post(result);
  }

  void _post(Map<String, Object> message) {
    _log('→ ${message['type']}');
    _controller.runJavaScript(receiveScript(message)).catchError((Object _) => _log('${message['type']} 전송 실패'));
  }

  NavigationDecision _onNavigationRequest(NavigationRequest request) {
    switch (classifyNavigation(request.url, widget.appUri, isMainFrame: request.isMainFrame)) {
      case NavigationTarget.app:
        return NavigationDecision.navigate;
      case NavigationTarget.external:
        _log('앱 밖 이동 → 외부로 연다');
        _openExternal(request.url);
        return NavigationDecision.prevent;
      case NavigationTarget.blocked:
        _log('앱 밖 하위 프레임 이동을 막았다');
        return NavigationDecision.prevent;
    }
  }

  Future<void> _openExternal(String url) async {
    final uri = Uri.tryParse(url);
    var opened = false;
    if (uri != null) {
      try {
        opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
      } on PlatformException {
        opened = false;
      }
    }
    if (!opened) _log('openExternal 실패');
  }

  void _onWebResourceError(WebResourceError error) {
    if (!_isPageLoadFailure(error)) return;
    _log('페이지를 불러오지 못했다(${error.errorType?.name ?? error.errorCode})');
    setState(() => _offline = true);
  }

  /// 앱 주소 자체를 못 불러온 경우만. 하위 자원 실패와, 우리가 막은 이동이 iOS에서 실패로 오는 것(-999 취소, 102 정책으로 중단)은 아니다
  bool _isPageLoadFailure(WebResourceError error) {
    if (error.isForMainFrame == false) return false;
    if (error.errorCode == -999 || error.errorCode == 102) return false;
    final url = error.url == null ? null : Uri.tryParse(error.url!);
    return url == null || isSameOrigin(url, widget.appUri);
  }

  void _retry() {
    setState(() => _offline = false);
    _controller.loadRequest(widget.appUri);
  }

  /// Android 뒤로 가기. 웹이 처리했으면(true) 끝, 더 갈 곳이 없으면 앱을 뒤로 보낸다
  Future<void> _onBack() async {
    var handled = false;
    if (!_offline) {
      try {
        handled = isTrueResult(await _controller.runJavaScriptReturningResult(onBackScript));
      } on Object {
        handled = false;
      }
    }
    _log('뒤로 가기 → ${handled ? '웹이 처리' : '앱 종료'}');
    if (!handled) await SystemNavigator.pop();
  }

  void _log(String text) {
    if (kDebugMode) debugPrint('[host] $text');
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _onBack();
      },
      // 상태 표시줄 영역까지 WebView가 덮고 웹이 env()·--inset-*로 비킨다. 네이티브 패딩을 두지 않는다
      child: Scaffold(
        backgroundColor: Colors.white,
        body: Stack(
          children: [
            WebViewWidget(controller: _controller),
            if (_offline) OfflineView(onRetry: _retry, onCall119: () => _openExternal('tel:119')),
          ],
        ),
      ),
    );
  }
}
