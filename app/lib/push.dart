// 앱 푸시 알림(app-front/README.md "호스트 계약" pushRegister·pushUnregister·pushToken·pushOpen, app-front backlog 07).
// - Firebase 값은 --dart-define(FIREBASE_*)으로 받는다. 값이 없거나 초기화에 실패하면 push 기능이 없을 뿐 앱은 그대로다.
// - 알림 권한은 웹이 pushRegister를 보낼 때(첫 센터 요청 뒤) 묻는다. 앱을 처음 열 때 묻지 않는다.
// - 앱이 앞에 있을 때 온 알림은 띄우지 않는다(FCM 기본값 그대로, 결정 5).
// - FCM 토큰·caseId·알림 본문은 로그에 찍지 않는다. 오류 기록은 종류만 남긴다.
// - 등록 토큰 API(getToken·onTokenRefresh·deleteToken)를 쓴다. firebase_messaging 17이 Firebase 설치 ID(FID) 직접 발송
//   (register·onRegistered)을 새로 들이며 이 셋을 deprecated로 두었지만, 서버(backend 28)는 FCM HTTP v1의 등록 토큰으로 보낸다(메모).

import 'dart:async';
import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'bridge.dart';

/// Firebase 앱 값(app/README.md "푸시 알림"). 비밀 키가 아니지만 프로젝트마다 달라 코드에 적지 않는다
const String firebaseApiKey = String.fromEnvironment('FIREBASE_API_KEY');
const String firebaseAppIdAndroid = String.fromEnvironment('FIREBASE_APP_ID_ANDROID');
const String firebaseAppIdIos = String.fromEnvironment('FIREBASE_APP_ID_IOS');
const String firebaseSenderId = String.fromEnvironment('FIREBASE_SENDER_ID');
const String firebaseProjectId = String.fromEnvironment('FIREBASE_PROJECT_ID');

/// iOS가 APNs 토큰을 줄 때까지 기다리는 시간. 없으면(Developer 계정·APNs 키 없음) failed로 끝난다
const Duration apnsTokenWait = Duration(seconds: 10);

/// Firebase 웹 API 키 모양. iOS SDK(FIRInstallations)는 모양이 틀리면 Dart가 잡을 수 없는 네이티브 예외로 앱을 멈추므로 먼저 거른다
final RegExp _apiKeyPattern = RegExp(r'^AIza[0-9A-Za-z_-]{35}$');

/// Firebase 앱 ID 모양(1:<프로젝트 번호>:<플랫폼>:<16진수>). 다른 플랫폼의 앱 ID는 받지 않는다
bool _isAppId(String appId, {required bool isIOS}) =>
    RegExp('^1:[0-9]+:${isIOS ? 'ios' : 'android'}:[0-9a-f]+\$').hasMatch(appId);

/// 이 플랫폼의 Firebase 값이 모두 있고 모양이 맞으면 옵션, 아니면 null(push 없음)
FirebaseOptions? firebaseOptionsFor({
  required bool isIOS,
  required String apiKey,
  required String appIdAndroid,
  required String appIdIos,
  required String senderId,
  required String projectId,
}) {
  final appId = isIOS ? appIdIos : appIdAndroid;
  if ([apiKey, appId, senderId, projectId].any((v) => v.isEmpty)) return null;
  if (!_apiKeyPattern.hasMatch(apiKey) || !_isAppId(appId, isIOS: isIOS)) return null;
  return FirebaseOptions(apiKey: apiKey, appId: appId, messagingSenderId: senderId, projectId: projectId);
}

class NativePush {
  NativePush({required this.post, required this.onOpen, required this.log});

  /// 웹에 메시지를 보낸다(pushToken)
  final void Function(Map<String, Object> message) post;

  /// 근로자가 센터 알림을 눌러 앱이 열렸다
  final void Function(String caseId) onOpen;
  final void Function(String text) log;

  bool _available = false;

  /// 이 페이지가 pushRegister를 보낸 적이 있다. 그때만 토큰 갱신을 알린다
  bool _registered = false;
  final List<StreamSubscription<Object?>> _subs = [];

  /// Firebase가 초기화됐다 = init.features에 push를 넣는다
  bool get available => _available;

  /// 앱 시작 때 한 번. 꺼져 있다가 알림으로 열린 경우(getInitialMessage)도 여기서 onOpen으로 넘긴다
  Future<bool> init() async {
    final options = firebaseOptionsFor(
      isIOS: Platform.isIOS,
      apiKey: firebaseApiKey,
      appIdAndroid: firebaseAppIdAndroid,
      appIdIos: firebaseAppIdIos,
      senderId: firebaseSenderId,
      projectId: firebaseProjectId,
    );
    if (options == null) return false;
    try {
      await Firebase.initializeApp(options: options);
      final messaging = FirebaseMessaging.instance;
      _subs.add(FirebaseMessaging.onMessageOpenedApp.listen(_onOpened));
      _subs.add(
        // ignore: deprecated_member_use
        messaging.onTokenRefresh.listen((token) {
          if (_registered) post(pushTokenMessage(token));
        }),
      );
      final initial = await messaging.getInitialMessage();
      if (initial != null) _onOpened(initial);
    } on Object catch (e) {
      log('Firebase 초기화 실패(${e.runtimeType})');
      return false;
    }
    _available = true;
    return true;
  }

  void _onOpened(RemoteMessage message) {
    final caseId = pushCaseIdOf(message.data);
    log('알림으로 열림${caseId == null ? '(무시)' : ''}');
    if (caseId != null) onOpen(caseId);
  }

  /// 새 페이지(ready). 그 페이지가 pushRegister를 보내기 전에는 토큰 갱신을 보내지 않는다
  void resetPage() => _registered = false;

  /// pushRegister: 권한을 묻고(처음 한 번) 토큰을 pushToken으로 한 번 보낸다
  Future<void> register() async {
    if (!_available) {
      post(pushTokenFailure(denied: false));
      return;
    }
    _registered = true;
    final messaging = FirebaseMessaging.instance;
    try {
      final settings = await messaging.requestPermission();
      if (settings.authorizationStatus == AuthorizationStatus.denied) {
        log('알림 권한 거부');
        post(pushTokenFailure(denied: true));
        return;
      }
      if (Platform.isIOS && !await _waitApnsToken(messaging)) {
        log('APNs 토큰 없음');
        post(pushTokenFailure(denied: false));
        return;
      }
      // ignore: deprecated_member_use
      final token = await messaging.getToken();
      post(token == null || token.isEmpty ? pushTokenFailure(denied: false) : pushTokenMessage(token));
    } on Object catch (e) {
      log('pushRegister 실패(${e is FirebaseException ? e.code : e.runtimeType})');
      post(pushTokenFailure(denied: false));
    }
  }

  Future<bool> _waitApnsToken(FirebaseMessaging messaging) async {
    final until = DateTime.now().add(apnsTokenWait);
    while (DateTime.now().isBefore(until)) {
      if (await messaging.getAPNSToken() != null) return true;
      await Future<void>.delayed(const Duration(milliseconds: 500));
    }
    return false;
  }

  /// pushUnregister: FCM 토큰을 지운다. 그 토큰으로 온 발송은 FCM이 거절하고 서버가 지운다
  Future<void> unregister() async {
    _registered = false;
    if (!_available) return;
    try {
      // ignore: deprecated_member_use
      await FirebaseMessaging.instance.deleteToken();
    } on Object catch (e) {
      log('pushUnregister 실패(${e is FirebaseException ? e.code : e.runtimeType})');
    }
  }

  void dispose() {
    for (final s in _subs) {
      s.cancel();
    }
  }
}
