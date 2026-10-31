// 호스트 계약(app-front/README.md "호스트 계약")의 호스트 쪽 메시지. 계약이 바뀌면 그 문서를 먼저 고친다.
// - 웹 → 호스트: JavaScript 채널 ForNav로 JSON 문자열(ready, openExternal, googleSignIn, speechStart, speechStop, pushRegister, pushUnregister).
// - 호스트 → 웹: window.fornav.receive(객체)(init, insets, googleSignInResult, speech, speechError, pushToken, pushOpen), 동기 window.fornav.onBack().
// - 메시지 본문(특히 openExternal.url, googleSignInResult.idToken, speech.text, pushToken.token, pushOpen.caseId)은 로그에 찍지 않는다. type만 남긴다.

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
bool isSignInCanceled(Object error) =>
    error is GoogleSignInException && error.code == GoogleSignInExceptionCode.canceled;

/// 네이티브 로그인을 켤 수 있는 빌드인가. Android는 웹 클라이언트 ID(serverClientId)만, iOS는 iOS 클라이언트 ID도 있어야 한다
bool nativeSignInConfigured({required bool isIOS, required String webClientId, required String iosClientId}) =>
    webClientId.isNotEmpty && (!isIOS || iosClientId.isNotEmpty);

/// init.features 값. 네이티브 음성 인식으로 통화 자막을 받아쓸 수 있다(app-front backlog 04)
const String featureSpeech = 'speech';

/// speechStart의 lang. 형식이 틀리면 null(무시한다)
String? speechLangOf(Map<String, dynamic> message) {
  final lang = message['lang'];
  return lang is String && lang.trim().isNotEmpty ? lang.trim() : null;
}

/// 받아쓴 글. 본문이므로 로그에 찍지 않는다
Map<String, Object> speechMessage(String text, {required bool isFinal}) => {
  'protocol': protocol,
  'type': 'speech',
  'text': text,
  'final': isFinal,
};

/// speechError.error 값
enum SpeechErrorKind { denied, unsupported }

Map<String, Object> speechErrorMessage(SpeechErrorKind kind) => {
  'protocol': protocol,
  'type': 'speechError',
  'error': kind.name,
};

/// 결과 없이 이어진 오류가 이만큼이면 끈다. 웹의 SPEECH_MAX_NETWORK_ERRORS와 같은 뜻이다
const int speechMaxErrorsInRow = 3;

/// 말이 없을 때 플랫폼이 내는 오류. 다시 켜면 되고 세지 않는다
const Set<String> _speechSilenceErrors = {'error_no_match', 'error_speech_timeout', 'error_busy', 'error_retry'};

/// 다시 켜지 않는 오류(권한·언어·인식기 없음)
const Map<String, SpeechErrorKind> _speechFatalErrors = {
  'error_permission': SpeechErrorKind.denied,
  'error_language_not_supported': SpeechErrorKind.unsupported,
  'error_language_unavailable': SpeechErrorKind.unsupported,
  'error_speech_recognizer_disabled': SpeechErrorKind.unsupported,
  'error_assets_not_installed': SpeechErrorKind.unsupported,
};

/// 이어진 오류로 셀 오류인가. 말 없음은 조용한 통화에서 계속 나므로 세지 않는다
bool speechErrorCounts(String errorMsg) => !_speechSilenceErrors.contains(errorMsg);

/// speech_to_text 오류 이름 → 끌 이유. null이면 다시 켠다. errorsInRow는 speechErrorCounts인 오류만 센 수다
SpeechErrorKind? speechErrorKind(String errorMsg, {required int errorsInRow}) {
  final fatal = _speechFatalErrors[errorMsg];
  if (fatal != null) return fatal;
  if (_speechSilenceErrors.contains(errorMsg)) return null;
  return errorsInRow >= speechMaxErrorsInRow ? SpeechErrorKind.unsupported : null;
}

/// WebView의 권한 요청 가운데 허용할 수 있는 것. 웹은 통화 마이크만 쓴다(카메라 영상은 쓰지 않는다)
bool isMicrophoneOnlyRequest(Set<String> types) => types.isNotEmpty && types.every((t) => t == 'microphone');

/// 파일 선택기가 사진을 고르는가. accept가 비었으면 모든 파일이라 사진도 된다
bool acceptsImages(List<String> acceptTypes) {
  final types = acceptTypes.expand((t) => t.split(',')).map((t) => t.trim().toLowerCase()).where((t) => t.isNotEmpty);
  return types.isEmpty ||
      types.any(
        (t) => t == '*/*' || t.startsWith('image/') || const {'.jpg', '.jpeg', '.png', '.heic', '.webp'}.contains(t),
      );
}

/// init.features 값. FCM 푸시 알림을 받을 수 있다(app-front backlog 07)
const String featurePush = 'push';

/// FCM 등록 토큰. 알림을 보낼 주소라 웹이 서버에 등록한다. 로그에 찍지 않는다
Map<String, Object> pushTokenMessage(String token) => {'protocol': protocol, 'type': 'pushToken', 'token': token};

/// pushRegister의 실패 응답. error는 denied(알림 권한 거부) | failed(그 밖)
Map<String, Object> pushTokenFailure({required bool denied}) => {
  'protocol': protocol,
  'type': 'pushToken',
  'error': denied ? 'denied' : 'failed',
};

/// 근로자가 센터 알림을 눌러 앱이 열렸다. caseId는 사례 번호일 뿐 내용이 아니다
Map<String, Object> pushOpenMessage(String caseId) => {'protocol': protocol, 'type': 'pushOpen', 'caseId': caseId};

/// 서버가 만드는 사례 id 모양(C-251031-001, 데모 C-02 등)
final RegExp _caseIdPattern = RegExp(r'^C-[0-9A-Za-z-]{1,40}$');

/// 알림의 data에서 열 사례 id. 센터 알림(kind == center)이고 사례 id 모양일 때만, 아니면 null(무시한다)
String? pushCaseIdOf(Map<String, dynamic> data) {
  final caseId = data['caseId'];
  if (data['kind'] != 'center' || caseId is! String) return null;
  return _caseIdPattern.hasMatch(caseId) ? caseId : null;
}

/// 알림으로 열린 사례를 웹이 받을 수 있을 때(init 뒤)까지 들고 있는다. 그 사이 여러 번 누르면 마지막 것만 남는다
class PushOpenGate {
  bool _open = false;
  String? _held;

  /// 알림을 눌렀다. 지금 보낼 수 있으면 caseId를, 아니면 들고 null을 돌려준다
  String? tap(String caseId) {
    if (_open) return caseId;
    _held = caseId;
    return null;
  }

  /// init을 보냈다. 들고 있던 것을 한 번 돌려주고 비운다
  String? opened() {
    _open = true;
    final held = _held;
    _held = null;
    return held;
  }

  /// 페이지가 다시 불렸다(ready). 다음 init까지 들고 있는다
  void close() => _open = false;
}
