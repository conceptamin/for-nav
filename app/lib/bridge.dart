// 호스트 계약(app-front/README.md "호스트 계약")의 호스트 쪽 메시지. 계약이 바뀌면 그 문서를 먼저 고친다.
// - 웹 → 호스트: JavaScript 채널 ForNav로 JSON 문자열(ready, openExternal, googleSignIn).
// - 호스트 → 웹: window.fornav.receive(객체)(init, insets, googleSignInResult), 동기 window.fornav.onBack().
// - 메시지 본문(특히 openExternal.url, googleSignInResult.idToken)은 로그에 찍지 않는다. type만 남긴다.

import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:google_sign_in/google_sign_in.dart';

const int protocol = 1;

/// 웹 → 호스트 채널 이름. 웹은 window.ForNav.postMessage가 있으면 호스트 안이라고 본다
const String channelName = 'ForNav';

/// 웹이 보낸 JSON 문자열을 객체로. 형식이 틀리거나 type이 없으면 null(무시한다)
Map<String, dynamic>? parseMessage(String raw) {
  try {
    final decoded = jsonDecode(raw);
    if (decoded is Map<String, dynamic> && decoded['type'] is String) return decoded;
  } on FormatException {
    // 무시한다
  }
  return null;
}

/// MediaQuery.padding은 논리 픽셀이고 WebView 안 CSS px와 같은 단위다. 키보드(viewInsets)는 넣지 않는다
Map<String, double> insetsOf(EdgeInsets padding) => {
  'top': padding.top,
  'right': padding.right,
  'bottom': padding.bottom,
  'left': padding.left,
};

/// init.features 값. 네이티브 Google 로그인을 할 수 있다(app-front backlog 06)
const String featureGoogleSignIn = 'googleSignIn';

/// features가 비면 필드를 넣지 않는다(웹은 없으면 빈 배열로 본다)
Map<String, Object> initMessage({
  required String platform,
  required String appVersion,
  required String locale,
  required EdgeInsets padding,
  List<String> features = const [],
}) => {
  'protocol': protocol,
  'type': 'init',
  'platform': platform,
  'appVersion': appVersion,
  'locale': locale,
  'insets': insetsOf(padding),
  if (features.isNotEmpty) 'features': features,
};

Map<String, Object> insetsMessage(EdgeInsets padding) => {
  'protocol': protocol,
  'type': 'insets',
  'insets': insetsOf(padding),
};

/// 웹에 메시지를 넘기는 스크립트. JSON은 그대로 JavaScript 객체 리터럴이다.
/// window.fornav는 웹이 만들므로 아직 없으면(로드 전) 아무 일도 하지 않는다
String receiveScript(Map<String, Object> message) => 'window.fornav?.receive(${jsonEncode(message)})';

const String onBackScript = 'window.fornav?.onBack?.() ?? false';

/// runJavaScriptReturningResult의 불리언은 플랫폼마다 bool·"true"·1로 온다
bool isTrueResult(Object? result) => result == true || result == 'true' || result == 1;

/// googleSignIn의 성공 응답. 토큰은 이 메시지로 웹에 한 번 넘기고 호스트에 남기지 않는다
Map<String, Object> googleSignInSuccess(String idToken) => {
  'protocol': protocol,
  'type': 'googleSignInResult',
  'idToken': idToken,
};

/// googleSignIn의 실패 응답. error는 canceled(사용자가 닫음) | failed(그 밖)
Map<String, Object> googleSignInFailure({required bool canceled}) => {
  'protocol': protocol,
  'type': 'googleSignInResult',
  'error': canceled ? 'canceled' : 'failed',
};

/// 사용자가 계정 선택을 닫은 것만 canceled다. 설정 오류·네트워크·Google Play 서비스 없음은 failed
bool isSignInCanceled(Object error) => error is GoogleSignInException && error.code == GoogleSignInExceptionCode.canceled;

/// 네이티브 로그인을 켤 수 있는 빌드인가. Android는 웹 클라이언트 ID(serverClientId)만, iOS는 iOS 클라이언트 ID도 있어야 한다
bool nativeSignInConfigured({required bool isIOS, required String webClientId, required String iosClientId}) =>
    webClientId.isNotEmpty && (!isIOS || iosClientId.isNotEmpty);
